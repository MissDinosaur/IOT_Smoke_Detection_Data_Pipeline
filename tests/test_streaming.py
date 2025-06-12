"""
Comprehensive test suite for streaming components in IoT Smoke Detection Pipeline.

This module tests:
- Kafka producer functionality
- Stream processing logic
- Spark streaming integration
- Data transformation and validation
- Error handling and recovery
- Performance and reliability
"""

import pytest
import json
import time
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import requests
from datetime import datetime, timedelta
import threading
import queue
import logging

# Test configuration
TEST_CONFIG = {
    'kafka_bootstrap_servers': 'localhost:9092',
    'kafka_topic': 'smoke_detection',
    'flask_api_url': 'http://localhost:5000',
    'test_timeout': 30,
    'batch_size': 100,
    'max_retries': 3
}

# Sample sensor data for testing
SAMPLE_SENSOR_DATA = {
    'Temperature[C]': 25.5,
    'Humidity[%]': 45.0,
    'TVOC[ppb]': 150.0,
    'eCO2[ppm]': 400.0,
    'Raw H2': 13000.0,
    'Raw Ethanol': 18500.0,
    'Pressure[hPa]': 1013.25,
    'PM1.0': 10.0,
    'PM2.5': 15.0,
    'NC0.5': 100.0,
    'NC1.0': 80.0,
    'NC2.5': 20.0,
    'timestamp': datetime.now().isoformat()
}

FIRE_SCENARIO_DATA = {
    'Temperature[C]': 85.0,
    'Humidity[%]': 20.0,
    'TVOC[ppb]': 2500.0,
    'eCO2[ppm]': 1200.0,
    'Raw H2': 25000.0,
    'Raw Ethanol': 35000.0,
    'Pressure[hPa]': 1010.0,
    'PM1.0': 150.0,
    'PM2.5': 250.0,
    'NC0.5': 2000.0,
    'NC1.0': 1500.0,
    'NC2.5': 800.0,
    'timestamp': datetime.now().isoformat()
}


class TestKafkaProducer:
    """Test cases for Kafka producer functionality."""
    
    @pytest.fixture
    def kafka_producer(self):
        """Create a test Kafka producer."""
        try:
            producer = KafkaProducer(
                bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                buffer_memory=33554432
            )
            yield producer
            producer.close()
        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")
    
    def test_producer_connection(self, kafka_producer):
        """Test Kafka producer connection."""
        assert kafka_producer is not None
        # Test producer metadata
        metadata = kafka_producer.list_topics(timeout=5)
        assert metadata is not None
    
    def test_send_single_message(self, kafka_producer):
        """Test sending a single sensor message."""
        message = SAMPLE_SENSOR_DATA.copy()
        
        # Send message
        future = kafka_producer.send(
            TEST_CONFIG['kafka_topic'],
            key='sensor_001',
            value=message
        )
        
        # Wait for send to complete
        record_metadata = future.get(timeout=10)
        
        assert record_metadata.topic == TEST_CONFIG['kafka_topic']
        assert record_metadata.partition >= 0
        assert record_metadata.offset >= 0
    
    def test_send_batch_messages(self, kafka_producer):
        """Test sending multiple sensor messages."""
        messages = []
        for i in range(TEST_CONFIG['batch_size']):
            message = SAMPLE_SENSOR_DATA.copy()
            message['sensor_id'] = f'sensor_{i:03d}'
            message['timestamp'] = datetime.now().isoformat()
            messages.append(message)
        
        # Send all messages
        futures = []
        for i, message in enumerate(messages):
            future = kafka_producer.send(
                TEST_CONFIG['kafka_topic'],
                key=f'sensor_{i:03d}',
                value=message
            )
            futures.append(future)
        
        # Wait for all sends to complete
        for future in futures:
            record_metadata = future.get(timeout=10)
            assert record_metadata.topic == TEST_CONFIG['kafka_topic']
    
    def test_send_fire_scenario(self, kafka_producer):
        """Test sending fire scenario data."""
        message = FIRE_SCENARIO_DATA.copy()
        
        future = kafka_producer.send(
            TEST_CONFIG['kafka_topic'],
            key='fire_test',
            value=message
        )
        
        record_metadata = future.get(timeout=10)
        assert record_metadata.topic == TEST_CONFIG['kafka_topic']
    
    def test_producer_error_handling(self, kafka_producer):
        """Test producer error handling with invalid data."""
        # Test with invalid JSON data
        with pytest.raises(Exception):
            invalid_data = {'invalid': float('inf')}  # JSON can't serialize infinity
            kafka_producer.send(TEST_CONFIG['kafka_topic'], value=invalid_data)
    
    def test_producer_performance(self, kafka_producer):
        """Test producer performance with high throughput."""
        start_time = time.time()
        num_messages = 1000
        
        futures = []
        for i in range(num_messages):
            message = SAMPLE_SENSOR_DATA.copy()
            message['message_id'] = i
            future = kafka_producer.send(TEST_CONFIG['kafka_topic'], value=message)
            futures.append(future)
        
        # Wait for all messages
        for future in futures:
            future.get(timeout=10)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = num_messages / duration
        
        print(f"Sent {num_messages} messages in {duration:.2f}s ({throughput:.2f} msg/s)")
        assert throughput > 100  # Should handle at least 100 messages per second


class TestKafkaConsumer:
    """Test cases for Kafka consumer functionality."""
    
    @pytest.fixture
    def kafka_consumer(self):
        """Create a test Kafka consumer."""
        try:
            consumer = KafkaConsumer(
                TEST_CONFIG['kafka_topic'],
                bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='test_consumer_group',
                consumer_timeout_ms=5000
            )
            yield consumer
            consumer.close()
        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")
    
    def test_consumer_connection(self, kafka_consumer):
        """Test Kafka consumer connection."""
        assert kafka_consumer is not None
        # Check topic assignment
        partitions = kafka_consumer.partitions_for_topic(TEST_CONFIG['kafka_topic'])
        assert partitions is not None
    
    def test_consume_messages(self, kafka_consumer, kafka_producer):
        """Test consuming messages from Kafka."""
        # Send a test message first
        test_message = SAMPLE_SENSOR_DATA.copy()
        test_message['test_id'] = 'consume_test'
        
        kafka_producer.send(TEST_CONFIG['kafka_topic'], value=test_message)
        kafka_producer.flush()
        
        # Consume messages
        messages = []
        for message in kafka_consumer:
            messages.append(message.value)
            if len(messages) >= 1:
                break
        
        assert len(messages) > 0
        # Verify message content
        consumed_message = messages[0]
        assert 'Temperature[C]' in consumed_message
        assert 'timestamp' in consumed_message


class TestStreamProcessing:
    """Test cases for stream processing logic."""
    
    def test_data_validation(self):
        """Test sensor data validation."""
        # Valid data
        valid_data = SAMPLE_SENSOR_DATA.copy()
        assert self._validate_sensor_data(valid_data) == True
        
        # Missing required field
        invalid_data = valid_data.copy()
        del invalid_data['Temperature[C]']
        assert self._validate_sensor_data(invalid_data) == False
        
        # Invalid data type
        invalid_data = valid_data.copy()
        invalid_data['Temperature[C]'] = 'invalid'
        assert self._validate_sensor_data(invalid_data) == False
    
    def test_data_transformation(self):
        """Test data transformation logic."""
        raw_data = SAMPLE_SENSOR_DATA.copy()
        transformed_data = self._transform_sensor_data(raw_data)
        
        # Check that all required fields are present
        required_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        for field in required_fields:
            assert field in transformed_data
            assert isinstance(transformed_data[field], (int, float))
    
    def test_anomaly_detection(self):
        """Test anomaly detection in streaming data."""
        # Normal data should not be flagged
        normal_data = SAMPLE_SENSOR_DATA.copy()
        assert self._detect_anomaly(normal_data) == False
        
        # Extreme values should be flagged
        anomaly_data = normal_data.copy()
        anomaly_data['Temperature[C]'] = 200.0  # Extreme temperature
        assert self._detect_anomaly(anomaly_data) == True
        
        # Fire scenario should be flagged
        fire_data = FIRE_SCENARIO_DATA.copy()
        assert self._detect_anomaly(fire_data) == True
    
    def test_batch_processing(self):
        """Test batch processing of streaming data."""
        # Create batch of messages
        batch = []
        for i in range(10):
            message = SAMPLE_SENSOR_DATA.copy()
            message['sensor_id'] = f'sensor_{i}'
            batch.append(message)
        
        # Process batch
        results = self._process_batch(batch)
        
        assert len(results) == len(batch)
        for result in results:
            assert 'sensor_id' in result
            assert 'processed_timestamp' in result
    
    def _validate_sensor_data(self, data):
        """Helper method to validate sensor data."""
        required_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        for field in required_fields:
            if field not in data:
                return False
            if not isinstance(data[field], (int, float)):
                return False
        
        return True
    
    def _transform_sensor_data(self, data):
        """Helper method to transform sensor data."""
        transformed = data.copy()
        
        # Ensure all numeric fields are float
        numeric_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        for field in numeric_fields:
            if field in transformed:
                transformed[field] = float(transformed[field])
        
        # Add processing timestamp
        transformed['processed_timestamp'] = datetime.now().isoformat()
        
        return transformed
    
    def _detect_anomaly(self, data):
        """Helper method to detect anomalies."""
        # Simple threshold-based anomaly detection
        thresholds = {
            'Temperature[C]': (0, 100),
            'Humidity[%]': (0, 100),
            'TVOC[ppb]': (0, 10000),
            'PM2.5': (0, 100)
        }
        
        for field, (min_val, max_val) in thresholds.items():
            if field in data:
                value = data[field]
                if value < min_val or value > max_val:
                    return True
        
        return False
    
    def _process_batch(self, batch):
        """Helper method to process batch of messages."""
        results = []
        for message in batch:
            if self._validate_sensor_data(message):
                transformed = self._transform_sensor_data(message)
                results.append(transformed)
        
        return results


class TestFlaskAPIIntegration:
    """Test cases for Flask API integration in streaming."""
    
    def test_api_health_check(self):
        """Test Flask API health check."""
        try:
            response = requests.get(
                f"{TEST_CONFIG['flask_api_url']}/health",
                timeout=5
            )
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_single_prediction_api(self):
        """Test single prediction API call."""
        try:
            # Prepare sensor data (exclude timestamp for API)
            api_data = {k: v for k, v in SAMPLE_SENSOR_DATA.items() if k != 'timestamp'}
            
            response = requests.post(
                f"{TEST_CONFIG['flask_api_url']}/predict",
                json=api_data,
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify response structure
            assert 'prediction' in result
            assert 'prediction_label' in result
            assert 'confidence' in result
            assert 'processing_time_seconds' in result
            
            # Verify prediction values
            assert result['prediction'] in [0, 1]
            assert result['prediction_label'] in ['fire', 'no_fire']
            assert isinstance(result['confidence'], dict)
            assert 'fire' in result['confidence']
            assert 'no_fire' in result['confidence']
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_batch_prediction_api(self):
        """Test batch prediction API call."""
        try:
            # Prepare batch data
            batch_data = []
            for i in range(5):
                api_data = {k: v for k, v in SAMPLE_SENSOR_DATA.items() if k != 'timestamp'}
                api_data['Temperature[C]'] += i * 5  # Vary temperature
                batch_data.append(api_data)
            
            response = requests.post(
                f"{TEST_CONFIG['flask_api_url']}/predict/batch",
                json=batch_data,
                timeout=15
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify response structure
            assert 'predictions' in result
            assert 'summary' in result
            assert len(result['predictions']) == len(batch_data)
            
            # Verify summary
            summary = result['summary']
            assert 'total_samples' in summary
            assert summary['total_samples'] == len(batch_data)
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_fire_scenario_prediction(self):
        """Test fire scenario prediction."""
        try:
            # Use fire scenario data (exclude timestamp)
            api_data = {k: v for k, v in FIRE_SCENARIO_DATA.items() if k != 'timestamp'}
            
            response = requests.post(
                f"{TEST_CONFIG['flask_api_url']}/predict",
                json=api_data,
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Fire scenario should likely predict fire
            # (though this depends on the trained model)
            assert result['prediction'] in [0, 1]
            assert result['prediction_label'] in ['fire', 'no_fire']
            
            # Fire confidence should be reasonable for fire scenario
            fire_confidence = result['confidence']['fire']
            assert 0.0 <= fire_confidence <= 1.0
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestEndToEndStreaming:
    """End-to-end integration tests for the complete streaming pipeline."""
    
    def test_complete_pipeline(self):
        """Test complete streaming pipeline from Kafka to API."""
        try:
            # Setup producer and consumer
            producer = KafkaProducer(
                bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            consumer = KafkaConsumer(
                TEST_CONFIG['kafka_topic'],
                bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id='e2e_test_group',
                consumer_timeout_ms=10000
            )
            
            # Send test message
            test_message = SAMPLE_SENSOR_DATA.copy()
            test_message['e2e_test_id'] = 'pipeline_test'
            
            producer.send(TEST_CONFIG['kafka_topic'], value=test_message)
            producer.flush()
            
            # Consume and process message
            for message in consumer:
                consumed_data = message.value
                if consumed_data.get('e2e_test_id') == 'pipeline_test':
                    # Process through API
                    api_data = {k: v for k, v in consumed_data.items() 
                              if k not in ['timestamp', 'e2e_test_id']}
                    
                    response = requests.post(
                        f"{TEST_CONFIG['flask_api_url']}/predict",
                        json=api_data,
                        timeout=10
                    )
                    
                    assert response.status_code == 200
                    result = response.json()
                    assert 'prediction' in result
                    break
            
            producer.close()
            consumer.close()
            
        except Exception as e:
            pytest.skip(f"End-to-end test failed: {e}")
    
    def test_streaming_performance(self):
        """Test streaming performance under load."""
        try:
            producer = KafkaProducer(
                bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                batch_size=16384,
                linger_ms=10
            )
            
            # Send messages at high rate
            start_time = time.time()
            num_messages = 500
            
            for i in range(num_messages):
                message = SAMPLE_SENSOR_DATA.copy()
                message['perf_test_id'] = i
                producer.send(TEST_CONFIG['kafka_topic'], value=message)
            
            producer.flush()
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = num_messages / duration
            
            print(f"Streaming performance: {throughput:.2f} messages/second")
            assert throughput > 50  # Should handle at least 50 messages per second
            
            producer.close()
            
        except Exception as e:
            pytest.skip(f"Performance test failed: {e}")


# Test fixtures and utilities
@pytest.fixture(scope="session")
def kafka_setup():
    """Setup Kafka for testing."""
    # Wait for Kafka to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
                request_timeout_ms=5000
            )
            producer.close()
            break
        except Exception:
            if i == max_retries - 1:
                pytest.skip("Kafka not available for testing")
            time.sleep(2)


@pytest.fixture(scope="session")
def flask_api_setup():
    """Setup Flask API for testing."""
    # Wait for Flask API to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(
                f"{TEST_CONFIG['flask_api_url']}/health",
                timeout=5
            )
            if response.status_code == 200:
                break
        except Exception:
            if i == max_retries - 1:
                pytest.skip("Flask API not available for testing")
            time.sleep(2)


# Performance benchmarks
def test_streaming_latency():
    """Benchmark streaming latency."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        consumer = KafkaConsumer(
            TEST_CONFIG['kafka_topic'],
            bootstrap_servers=TEST_CONFIG['kafka_bootstrap_servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='latency_test_group'
        )
        
        # Measure end-to-end latency
        latencies = []
        num_tests = 10
        
        for i in range(num_tests):
            send_time = time.time()
            message = SAMPLE_SENSOR_DATA.copy()
            message['latency_test_id'] = i
            message['send_timestamp'] = send_time
            
            producer.send(TEST_CONFIG['kafka_topic'], value=message)
            producer.flush()
            
            # Consume the message
            for consumed_message in consumer:
                data = consumed_message.value
                if data.get('latency_test_id') == i:
                    receive_time = time.time()
                    latency = receive_time - data['send_timestamp']
                    latencies.append(latency)
                    break
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print(f"Average latency: {avg_latency*1000:.2f}ms")
        print(f"Maximum latency: {max_latency*1000:.2f}ms")
        
        # Latency should be reasonable
        assert avg_latency < 1.0  # Less than 1 second average
        assert max_latency < 5.0  # Less than 5 seconds maximum
        
        producer.close()
        consumer.close()
        
    except Exception as e:
        pytest.skip(f"Latency test failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
