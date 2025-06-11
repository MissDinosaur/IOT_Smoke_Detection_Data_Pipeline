#!/usr/bin/env python3
"""
Historical Data ML Processor for IoT Smoke Detection.

This module processes historical sensor data using trained ML models to:
- Generate predictions on historical datasets
- Analyze model performance over time
- Create prediction reports and visualizations
- Validate model accuracy on historical data
- Generate training data for model improvement

Features:
- Batch processing of large historical datasets
- ML model integration for predictions
- Performance metrics calculation
- Data quality assessment
- Comprehensive reporting

Usage:
    python historical_ml_processor.py --input data/historical_data.csv --output results/
    python historical_ml_processor.py --input data/ --model ml/models/best_model.pkl --batch-size 1000
"""

import sys
import os
import argparse
import time
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import logging
from ml.inference.model_loader import SmokeDetectionModelLoader
from ml.inference.predict import SmokeDetectionPredictor
from data_processing.stream_processing.spark_streaming_processor import (
    MLPredictor, MLPredictionConfig, AlertManager, AlertThresholds
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("historical_ml_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("historical_ml_processor")


class HistoricalMLProcessor:
    """Processes historical data with ML predictions and analytics."""
    
    def __init__(self, model_path: str = None, batch_size: int = 1000):
        self.model_path = model_path or "/app/ml/models/best_model.pkl"
        self.batch_size = batch_size
        self.predictor = None
        self.ml_predictor = None
        self.alert_manager = AlertManager()
        self.results = []
        self.performance_metrics = {}
        
    def initialize_ml_model(self) -> bool:
        """Initialize ML model for predictions."""
        try:
            logger.info(f"Loading ML model from: {self.model_path}")
            
            # Initialize predictor
            self.predictor = SmokeDetectionPredictor(self.model_path)
            
            if self.predictor.model_loader.is_loaded:
                # Also initialize ML predictor for advanced features
                ml_config = MLPredictionConfig(
                    model_path=self.model_path,
                    enable_ml_predictions=True,
                    batch_prediction_size=self.batch_size
                )
                self.ml_predictor = MLPredictor(ml_config)
                self.ml_predictor.initialize_ml_model()
                
                logger.info("✅ ML model loaded successfully for historical processing")
                return True
            else:
                logger.error("❌ Failed to load ML model")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error initializing ML model: {e}")
            return False
    
    def process_historical_file(self, input_path: str, output_path: str = None) -> Dict[str, Any]:
        """Process a single historical data file."""
        logger.info(f"📁 Processing historical file: {input_path}")
        
        try:
            # Load historical data
            df = pd.read_csv(input_path)
            logger.info(f"📊 Loaded {len(df)} historical records")
            
            # Process in batches
            results = self.process_dataframe(df)
            
            # Save results if output path provided
            if output_path:
                self.save_results(results, output_path)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error processing file {input_path}: {e}")
            raise
    
    def process_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process DataFrame with ML predictions and analytics."""
        start_time = time.time()
        
        # Initialize results
        predictions = []
        alerts = []
        quality_issues = []
        
        # Process in batches
        total_batches = (len(df) + self.batch_size - 1) // self.batch_size
        logger.info(f"🔄 Processing {len(df)} records in {total_batches} batches")
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min((batch_idx + 1) * self.batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            logger.debug(f"Processing batch {batch_idx + 1}/{total_batches} "
                        f"(rows {start_idx}-{end_idx})")
            
            # Process batch
            batch_results = self.process_batch(batch_df, batch_idx)
            
            # Accumulate results
            predictions.extend(batch_results['predictions'])
            alerts.extend(batch_results['alerts'])
            quality_issues.extend(batch_results['quality_issues'])
        
        processing_time = time.time() - start_time
        
        # Calculate performance metrics
        performance_metrics = self.calculate_performance_metrics(df, predictions)
        
        # Generate summary
        summary = self.generate_summary(df, predictions, alerts, quality_issues, processing_time)
        
        return {
            'predictions': predictions,
            'alerts': alerts,
            'quality_issues': quality_issues,
            'performance_metrics': performance_metrics,
            'summary': summary,
            'processing_time': processing_time
        }
    
    def process_batch(self, batch_df: pd.DataFrame, batch_idx: int) -> Dict[str, Any]:
        """Process a single batch of historical data."""
        predictions = []
        alerts = []
        quality_issues = []
        
        for idx, row in batch_df.iterrows():
            try:
                # Convert row to sensor data dictionary
                sensor_data = self.row_to_sensor_data(row)
                
                # Make ML prediction
                if self.predictor:
                    prediction_result = self.predictor.predict_single(sensor_data)
                    
                    # Add row index and timestamp
                    prediction_result['row_index'] = idx
                    prediction_result['batch_index'] = batch_idx
                    
                    predictions.append(prediction_result)
                    
                    # Check for alerts based on prediction
                    if prediction_result.get('prediction') == 1:
                        alert = {
                            'type': 'ML_FIRE_PREDICTION',
                            'row_index': idx,
                            'confidence': prediction_result.get('confidence', 0.0),
                            'timestamp': prediction_result.get('timestamp'),
                            'sensor_data': sensor_data
                        }
                        alerts.append(alert)
                
                # Check for threshold-based alerts
                threshold_alerts = self.alert_manager.evaluate_alerts(
                    type('Row', (), sensor_data)()  # Convert dict to object
                )
                for alert in threshold_alerts:
                    alert['row_index'] = idx
                    alert['batch_index'] = batch_idx
                    alerts.append(alert)
                
                # Basic data quality check
                quality_score = self.assess_data_quality(sensor_data)
                if quality_score < 80:
                    quality_issues.append({
                        'row_index': idx,
                        'quality_score': quality_score,
                        'issues': self.identify_quality_issues(sensor_data)
                    })
                    
            except Exception as e:
                logger.error(f"❌ Error processing row {idx}: {e}")
                predictions.append({
                    'row_index': idx,
                    'error': str(e),
                    'prediction': 0,
                    'confidence': 0.0
                })
        
        return {
            'predictions': predictions,
            'alerts': alerts,
            'quality_issues': quality_issues
        }
    
    def row_to_sensor_data(self, row) -> Dict[str, Any]:
        """Convert DataFrame row to sensor data dictionary."""
        sensor_columns = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5", "CNT", "Fire Alarm"
        ]
        
        sensor_data = {}
        for col in sensor_columns:
            if col in row.index:
                sensor_data[col] = row[col]
            else:
                # Provide default values for missing columns
                sensor_data[col] = 0.0
        
        return sensor_data
    
    def assess_data_quality(self, sensor_data: Dict[str, Any]) -> float:
        """Assess data quality score for sensor data."""
        quality_score = 100.0
        
        # Check for missing values
        missing_count = sum(1 for v in sensor_data.values() if pd.isna(v))
        quality_score -= missing_count * 10
        
        # Check for extreme values
        if sensor_data.get("Temperature[C]", 0) > 100 or sensor_data.get("Temperature[C]", 0) < -50:
            quality_score -= 20
        
        if sensor_data.get("Humidity[%]", 0) > 100 or sensor_data.get("Humidity[%]", 0) < 0:
            quality_score -= 15
        
        if sensor_data.get("TVOC[ppb]", 0) < 0:
            quality_score -= 10
        
        return max(0, quality_score)
    
    def identify_quality_issues(self, sensor_data: Dict[str, Any]) -> List[str]:
        """Identify specific data quality issues."""
        issues = []
        
        # Check for missing values
        missing_fields = [k for k, v in sensor_data.items() if pd.isna(v)]
        if missing_fields:
            issues.append(f"Missing values: {', '.join(missing_fields)}")
        
        # Check for extreme values
        if sensor_data.get("Temperature[C]", 0) > 100:
            issues.append("Extreme high temperature")
        if sensor_data.get("Temperature[C]", 0) < -50:
            issues.append("Extreme low temperature")
        
        if sensor_data.get("Humidity[%]", 0) > 100:
            issues.append("Humidity above 100%")
        if sensor_data.get("Humidity[%]", 0) < 0:
            issues.append("Negative humidity")
        
        if sensor_data.get("TVOC[ppb]", 0) < 0:
            issues.append("Negative TVOC reading")
        
        return issues
    
    def calculate_performance_metrics(self, df: pd.DataFrame, predictions: List[Dict]) -> Dict[str, Any]:
        """Calculate ML model performance metrics."""
        if "Fire Alarm" not in df.columns:
            return {"error": "No ground truth available for performance calculation"}
        
        # Extract predictions and ground truth
        y_true = []
        y_pred = []
        y_prob = []
        
        for i, pred in enumerate(predictions):
            if 'error' not in pred and i < len(df):
                y_true.append(df.iloc[i]["Fire Alarm"])
                y_pred.append(pred.get('prediction', 0))
                
                # Extract probability for positive class
                prob = pred.get('probability', {})
                if isinstance(prob, dict):
                    y_prob.append(prob.get('fire', 0.5))
                else:
                    y_prob.append(0.5)
        
        if not y_true:
            return {"error": "No valid predictions for performance calculation"}
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        try:
            metrics = {
                'accuracy': accuracy_score(y_true, y_pred),
                'precision': precision_score(y_true, y_pred, zero_division=0),
                'recall': recall_score(y_true, y_pred, zero_division=0),
                'f1_score': f1_score(y_true, y_pred, zero_division=0),
                'total_samples': len(y_true),
                'fire_samples': sum(y_true),
                'predicted_fires': sum(y_pred)
            }
            
            # Calculate AUC if we have probabilities
            if len(set(y_true)) > 1:  # Need both classes for AUC
                metrics['auc'] = roc_auc_score(y_true, y_prob)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {"error": str(e)}
    
    def generate_summary(self, df: pd.DataFrame, predictions: List[Dict], 
                        alerts: List[Dict], quality_issues: List[Dict], 
                        processing_time: float) -> Dict[str, Any]:
        """Generate processing summary."""
        successful_predictions = [p for p in predictions if 'error' not in p]
        fire_predictions = [p for p in successful_predictions if p.get('prediction') == 1]
        
        return {
            'total_records': len(df),
            'successful_predictions': len(successful_predictions),
            'failed_predictions': len(predictions) - len(successful_predictions),
            'fire_predictions': len(fire_predictions),
            'fire_prediction_rate': len(fire_predictions) / len(successful_predictions) if successful_predictions else 0,
            'total_alerts': len(alerts),
            'ml_alerts': len([a for a in alerts if a.get('type') == 'ML_FIRE_PREDICTION']),
            'threshold_alerts': len([a for a in alerts if a.get('type') != 'ML_FIRE_PREDICTION']),
            'quality_issues': len(quality_issues),
            'processing_time': processing_time,
            'processing_rate': len(df) / processing_time if processing_time > 0 else 0
        }
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save processing results to files."""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save predictions
        predictions_file = output_dir / f"predictions_{timestamp}.json"
        with open(predictions_file, 'w') as f:
            json.dump(results['predictions'], f, indent=2, default=str)
        
        # Save alerts
        alerts_file = output_dir / f"alerts_{timestamp}.json"
        with open(alerts_file, 'w') as f:
            json.dump(results['alerts'], f, indent=2, default=str)
        
        # Save summary report
        report_file = output_dir / f"summary_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'summary': results['summary'],
                'performance_metrics': results['performance_metrics'],
                'processing_time': results['processing_time']
            }, f, indent=2, default=str)
        
        logger.info(f"📁 Results saved to {output_dir}")
        logger.info(f"   Predictions: {predictions_file}")
        logger.info(f"   Alerts: {alerts_file}")
        logger.info(f"   Report: {report_file}")


def main():
    """Main function for historical ML processing."""
    parser = argparse.ArgumentParser(description="Historical Data ML Processor")
    
    parser.add_argument("--input", "-i", required=True,
                       help="Input CSV file or directory path")
    parser.add_argument("--output", "-o", default="results/historical_ml",
                       help="Output directory for results")
    parser.add_argument("--model", "-m", default="/app/ml/models/best_model.pkl",
                       help="Path to trained ML model")
    parser.add_argument("--batch-size", "-b", type=int, default=1000,
                       help="Batch size for processing")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize processor
    processor = HistoricalMLProcessor(
        model_path=args.model,
        batch_size=args.batch_size
    )
    
    # Initialize ML model
    if not processor.initialize_ml_model():
        logger.error("❌ Failed to initialize ML model")
        return 1
    
    try:
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Process single file
            logger.info(f"🔄 Processing single file: {input_path}")
            results = processor.process_historical_file(str(input_path), args.output)
            
            # Print summary
            summary = results['summary']
            logger.info("📊 Processing Summary:")
            logger.info(f"   Total Records: {summary['total_records']}")
            logger.info(f"   Fire Predictions: {summary['fire_predictions']} ({summary['fire_prediction_rate']:.2%})")
            logger.info(f"   Total Alerts: {summary['total_alerts']}")
            logger.info(f"   Processing Rate: {summary['processing_rate']:.1f} records/sec")
            
            # Print performance metrics if available
            if 'error' not in results['performance_metrics']:
                metrics = results['performance_metrics']
                logger.info("🎯 Model Performance:")
                logger.info(f"   Accuracy: {metrics.get('accuracy', 0):.3f}")
                logger.info(f"   Precision: {metrics.get('precision', 0):.3f}")
                logger.info(f"   Recall: {metrics.get('recall', 0):.3f}")
                logger.info(f"   F1-Score: {metrics.get('f1_score', 0):.3f}")
                if 'auc' in metrics:
                    logger.info(f"   AUC: {metrics['auc']:.3f}")
            
        elif input_path.is_dir():
            # Process directory of files
            csv_files = list(input_path.glob("*.csv"))
            logger.info(f"🔄 Processing {len(csv_files)} CSV files in directory: {input_path}")
            
            for csv_file in csv_files:
                logger.info(f"📁 Processing: {csv_file.name}")
                output_subdir = Path(args.output) / csv_file.stem
                processor.process_historical_file(str(csv_file), str(output_subdir))
        
        else:
            logger.error(f"❌ Input path does not exist: {input_path}")
            return 1
        
        logger.info("✅ Historical ML processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error in historical processing: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
