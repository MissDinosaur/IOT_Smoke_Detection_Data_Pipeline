"""
Stream ML integration for real-time smoke detection predictions.
Integrates ML model with Kafka stream processing for live inference.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

# Project imports
from ml.inference.model_loader import get_model_loader
from ml.inference.predict import SmokeDetectionPredictor
from config.env_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_SMOKE
from data_processing.stream_processing.metrics_streaming import get_metrics_collector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_stream_inference.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ml_stream_inference")


class StreamMLProcessor:
    """Processes streaming data with ML predictions"""
    
    def __init__(self, model_path: str = None, 
                 input_topic: str = KAFKA_TOPIC_SMOKE,
                 output_topic: str = "smoke_predictions"):
        
        self.predictor = SmokeDetectionPredictor(model_path)
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.metrics_collector = get_metrics_collector()
        
        # Initialize Kafka components
        self.consumer = None
        self.producer = None
        self.prediction_count = 0
        self.fire_detection_count = 0
        
    def initialize_kafka(self) -> bool:
        """Initialize Kafka consumer and producer"""
        
        try:
            # Initialize consumer
            self.consumer = KafkaConsumer(
                self.input_topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='ml_prediction_group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            # Initialize producer
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            logger.info("Kafka consumer and producer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka: {e}")
            return False
    
    def process_stream(self, max_messages: int = None) -> None:
        """Process streaming data with ML predictions"""
        
        if not self.initialize_kafka():
            raise RuntimeError("Failed to initialize Kafka components")
        
        logger.info(f"Starting ML stream processing on topic: {self.input_topic}")
        logger.info(f"Publishing predictions to topic: {self.output_topic}")
        
        message_count = 0
        
        try:
            for message in self.consumer:
                start_time = time.time()
                
                try:
                    # Extract sensor data
                    sensor_data = message.value
                    
                    # Make prediction
                    prediction_result = self.predictor.predict_single(sensor_data)
                    
                    # Enhance prediction with metadata
                    enhanced_result = self._enhance_prediction(
                        sensor_data, prediction_result, message
                    )
                    
                    # Publish prediction
                    self._publish_prediction(enhanced_result)
                    
                    # Update metrics
                    processing_time = (time.time() - start_time) * 1000
                    self.metrics_collector.record_message_processed(
                        processing_time, 
                        quality_score=1.0 if 'error' not in prediction_result else 0.0
                    )
                    
                    # Update counters
                    self.prediction_count += 1
                    if prediction_result.get('prediction') == 1:
                        self.fire_detection_count += 1
                        self.metrics_collector.record_anomaly_detected()
                        self.metrics_collector.record_alert_triggered()
                    
                    # Log periodic updates
                    if self.prediction_count % 100 == 0:
                        logger.info(f"Processed {self.prediction_count} predictions, "
                                  f"{self.fire_detection_count} fire detections")
                    
                    message_count += 1
                    if max_messages and message_count >= max_messages:
                        logger.info(f"Reached maximum message limit: {max_messages}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.metrics_collector.record_message_failed()
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Stream processing interrupted by user")
        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            raise
        finally:
            self._cleanup()
    
    def _enhance_prediction(self, sensor_data: Dict[str, Any], 
                           prediction_result: Dict[str, Any],
                           kafka_message) -> Dict[str, Any]:
        """Enhance prediction with additional metadata"""
        
        enhanced = prediction_result.copy()
        
        # Add stream metadata
        enhanced['stream_metadata'] = {
            'kafka_topic': kafka_message.topic,
            'kafka_partition': kafka_message.partition,
            'kafka_offset': kafka_message.offset,
            'kafka_timestamp': kafka_message.timestamp,
            'processing_timestamp': datetime.now().isoformat(),
            'prediction_id': f"{kafka_message.partition}_{kafka_message.offset}"
        }
        
        # Add original sensor data
        enhanced['sensor_data'] = sensor_data
        
        # Add alert level based on prediction
        if prediction_result.get('prediction') == 1:
            confidence = prediction_result.get('confidence', 0)
            if confidence > 0.9:
                enhanced['alert_level'] = 'CRITICAL'
            elif confidence > 0.7:
                enhanced['alert_level'] = 'HIGH'
            else:
                enhanced['alert_level'] = 'MEDIUM'
        else:
            enhanced['alert_level'] = 'NONE'
        
        return enhanced
    
    def _publish_prediction(self, prediction: Dict[str, Any]) -> None:
        """Publish prediction to output topic"""
        
        try:
            self.producer.send(self.output_topic, value=prediction)
            self.producer.flush()
            
            # Log critical alerts
            if prediction.get('alert_level') in ['CRITICAL', 'HIGH']:
                logger.warning(f"FIRE ALERT: {prediction['prediction_label']} "
                             f"(Confidence: {prediction.get('confidence', 0):.3f})")
                
        except Exception as e:
            logger.error(f"Failed to publish prediction: {e}")
    
    def _cleanup(self) -> None:
        """Cleanup Kafka connections"""
        
        try:
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            logger.info("Kafka connections closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class StreamMLMonitor:
    """Monitors ML stream processing performance"""
    
    def __init__(self, prediction_topic: str = "smoke_predictions"):
        self.prediction_topic = prediction_topic
        self.consumer = None
        
    def monitor_predictions(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Monitor predictions for specified duration"""
        
        try:
            # Initialize consumer
            self.consumer = KafkaConsumer(
                self.prediction_topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='ml_monitor_group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            logger.info(f"Monitoring predictions for {duration_seconds} seconds...")
            
            start_time = time.time()
            predictions = []
            
            while time.time() - start_time < duration_seconds:
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        predictions.append(message.value)
            
            # Generate monitoring report
            report = self._generate_monitoring_report(predictions)
            
            return report
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            raise
        finally:
            if self.consumer:
                self.consumer.close()
    
    def _generate_monitoring_report(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate monitoring report from predictions"""
        
        total_predictions = len(predictions)
        fire_predictions = sum(1 for p in predictions if p.get('prediction') == 1)
        
        alert_levels = {}
        confidences = []
        
        for pred in predictions:
            alert_level = pred.get('alert_level', 'NONE')
            alert_levels[alert_level] = alert_levels.get(alert_level, 0) + 1
            
            if pred.get('confidence'):
                confidences.append(pred['confidence'])
        
        report = {
            'monitoring_period': {
                'start_time': datetime.now().isoformat(),
                'total_predictions': total_predictions,
                'predictions_per_minute': total_predictions if total_predictions > 0 else 0
            },
            'prediction_summary': {
                'fire_detections': fire_predictions,
                'no_fire_detections': total_predictions - fire_predictions,
                'fire_detection_rate': fire_predictions / total_predictions if total_predictions > 0 else 0
            },
            'alert_distribution': alert_levels,
            'confidence_stats': {
                'mean': sum(confidences) / len(confidences) if confidences else 0,
                'min': min(confidences) if confidences else 0,
                'max': max(confidences) if confidences else 0
            },
            'sample_predictions': predictions[:5]  # First 5 predictions as sample
        }
        
        return report


def main():
    """Main function for command-line interface"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Stream ML Integration for Smoke Detection')
    parser.add_argument('--model', type=str, help='Path to trained model file')
    parser.add_argument('--input-topic', type=str, default=KAFKA_TOPIC_SMOKE, 
                       help='Input Kafka topic')
    parser.add_argument('--output-topic', type=str, default='smoke_predictions',
                       help='Output Kafka topic for predictions')
    parser.add_argument('--max-messages', type=int, help='Maximum messages to process')
    parser.add_argument('--monitor', action='store_true', help='Monitor predictions instead of processing')
    parser.add_argument('--monitor-duration', type=int, default=60, 
                       help='Monitoring duration in seconds')
    
    args = parser.parse_args()
    
    try:
        if args.monitor:
            # Monitor mode
            monitor = StreamMLMonitor(args.output_topic)
            report = monitor.monitor_predictions(args.monitor_duration)
            
            print("\nML Stream Monitoring Report:")
            print(json.dumps(report, indent=2))
            
        else:
            # Processing mode
            processor = StreamMLProcessor(
                model_path=args.model,
                input_topic=args.input_topic,
                output_topic=args.output_topic
            )
            
            processor.process_stream(max_messages=args.max_messages)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
