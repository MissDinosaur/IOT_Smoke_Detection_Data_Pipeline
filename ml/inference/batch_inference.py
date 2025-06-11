"""
Batch inference script for IoT smoke detection.
Processes large datasets and saves predictions to files.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import pandas as pd
import numpy as np
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List

# Project imports
from ml.inference.model_loader import get_model_loader
from ml.inference.predict import SmokeDetectionPredictor
from config.constants import CLEANED_DATA_FILE
from app.utils.path_utils import DATA_DIR, build_relative_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("batch_inference")


class BatchInferenceProcessor:
    """Handles batch inference for smoke detection"""
    
    def __init__(self, model_path: str = None):
        self.predictor = SmokeDetectionPredictor(model_path)
        self.results = []
        
    def process_csv_file(self, input_file: str, output_file: str = None, 
                        batch_size: int = 1000) -> Dict[str, Any]:
        """Process CSV file in batches"""
        
        logger.info(f"Processing CSV file: {input_file}")
        
        try:
            # Load data
            df = pd.read_csv(input_file)
            logger.info(f"Loaded {len(df)} records")
            
            # Process in batches
            all_predictions = []
            total_batches = (len(df) + batch_size - 1) // batch_size
            
            for i in range(0, len(df), batch_size):
                batch_num = i // batch_size + 1
                logger.info(f"Processing batch {batch_num}/{total_batches}")
                
                batch_df = df.iloc[i:i+batch_size]
                
                # Make predictions
                batch_predictions = self.predictor.model_loader.predict_batch(batch_df)
                
                # Add metadata
                for j, pred in enumerate(batch_predictions):
                    pred['row_index'] = i + j
                    pred['batch_number'] = batch_num
                
                all_predictions.extend(batch_predictions)
            
            # Create results DataFrame
            results_df = self._create_results_dataframe(df, all_predictions)
            
            # Save results
            if output_file is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"ml/results/batch_predictions_{timestamp}.csv"
            
            # Create output directory
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            results_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            
            # Generate summary
            summary = self._generate_summary(all_predictions)
            
            return {
                'input_file': input_file,
                'output_file': output_file,
                'total_records': len(df),
                'predictions': all_predictions,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            raise
    
    def _create_results_dataframe(self, original_df: pd.DataFrame, 
                                 predictions: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create results DataFrame with original data and predictions"""
        
        # Create predictions DataFrame
        pred_data = []
        for pred in predictions:
            pred_data.append({
                'prediction': pred['prediction'],
                'prediction_label': pred['prediction_label'],
                'confidence': pred.get('confidence'),
                'fire_probability': pred.get('probability', {}).get('fire') if pred.get('probability') else None,
                'no_fire_probability': pred.get('probability', {}).get('no_fire') if pred.get('probability') else None,
                'row_index': pred.get('row_index'),
                'batch_number': pred.get('batch_number')
            })
        
        pred_df = pd.DataFrame(pred_data)
        
        # Combine with original data
        results_df = pd.concat([original_df.reset_index(drop=True), pred_df], axis=1)
        
        return results_df
    
    def _generate_summary(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for predictions"""
        
        total_predictions = len(predictions)
        fire_predictions = sum(1 for p in predictions if p['prediction'] == 1)
        no_fire_predictions = total_predictions - fire_predictions
        
        # Calculate confidence statistics
        confidences = [p.get('confidence', 0) for p in predictions if p.get('confidence')]
        
        summary = {
            'total_predictions': total_predictions,
            'fire_detections': fire_predictions,
            'no_fire_detections': no_fire_predictions,
            'fire_detection_rate': fire_predictions / total_predictions if total_predictions > 0 else 0,
            'confidence_stats': {
                'mean': np.mean(confidences) if confidences else 0,
                'std': np.std(confidences) if confidences else 0,
                'min': np.min(confidences) if confidences else 0,
                'max': np.max(confidences) if confidences else 0
            }
        }
        
        return summary
    
    def process_streaming_data(self, data_source: str, output_dir: str = "ml/results/streaming",
                              save_interval: int = 100) -> None:
        """Process streaming data and save predictions periodically"""
        
        logger.info(f"Starting streaming inference from {data_source}")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        predictions_buffer = []
        file_counter = 1
        
        try:
            # This is a placeholder for streaming data processing
            # In a real implementation, this would connect to a data stream
            logger.info("Streaming inference not implemented - use process_csv_file for batch processing")
            
        except Exception as e:
            logger.error(f"Error in streaming inference: {e}")
            raise
    
    def save_predictions_json(self, predictions: List[Dict[str, Any]], 
                             output_file: str) -> None:
        """Save predictions to JSON file"""
        
        # Create output directory
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for JSON serialization
        json_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_predictions': len(predictions),
                'model_info': self.predictor.get_model_info()
            },
            'predictions': predictions
        }
        
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        logger.info(f"Predictions saved to JSON: {output_file}")
    
    def generate_report(self, results: Dict[str, Any], report_file: str = None) -> str:
        """Generate detailed inference report"""
        
        if report_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"ml/reports/batch_inference_report_{timestamp}.json"
        
        # Create report directory
        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare report
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_type': 'batch_inference',
                'model_info': self.predictor.get_model_info()
            },
            'processing_info': {
                'input_file': results['input_file'],
                'output_file': results['output_file'],
                'total_records': results['total_records']
            },
            'summary_statistics': results['summary'],
            'detailed_predictions': results['predictions'][:10]  # First 10 for sample
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
        return report_file


def main():
    """Main function for command-line interface"""
    
    parser = argparse.ArgumentParser(description='Batch Inference for Smoke Detection')
    parser.add_argument('--model', type=str, help='Path to trained model file')
    parser.add_argument('--input', type=str, required=True, help='Input CSV file')
    parser.add_argument('--output', type=str, help='Output CSV file')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--json-output', type=str, help='Save predictions to JSON file')
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = BatchInferenceProcessor(args.model)
        
        # Process file
        logger.info("Starting batch inference...")
        results = processor.process_csv_file(
            input_file=args.input,
            output_file=args.output,
            batch_size=args.batch_size
        )
        
        # Print summary
        summary = results['summary']
        print("\nBatch Inference Summary:")
        print(f"Total Records: {results['total_records']}")
        print(f"Fire Detections: {summary['fire_detections']}")
        print(f"No Fire Detections: {summary['no_fire_detections']}")
        print(f"Fire Detection Rate: {summary['fire_detection_rate']:.2%}")
        print(f"Average Confidence: {summary['confidence_stats']['mean']:.3f}")
        print(f"Results saved to: {results['output_file']}")
        
        # Save JSON output if requested
        if args.json_output:
            processor.save_predictions_json(results['predictions'], args.json_output)
        
        # Generate report if requested
        if args.report:
            report_file = processor.generate_report(results)
            print(f"Detailed report saved to: {report_file}")
        
        logger.info("Batch inference completed successfully")
        
    except Exception as e:
        logger.error(f"Batch inference failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
