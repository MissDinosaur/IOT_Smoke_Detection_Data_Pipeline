"""
Prediction script for IoT smoke detection.
Provides command-line interface for making predictions on sensor data.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import json
import argparse
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

# Project imports
from ml.inference.model_loader import get_model_loader
from config.constants import CLEANED_DATA_FILE
from app.utils.path_utils import DATA_DIR, build_relative_path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("prediction")


class SmokeDetectionPredictor:
    """Handles smoke detection predictions"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_loader = get_model_loader(model_path)

    def predict_single(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make prediction on single sensor reading"""

        try:
            # Validate input
            validation = self.model_loader.validate_input(sensor_data)
            if not validation["is_valid"]:
                return {
                    "error": "Invalid input data",
                    "validation_errors": validation["errors"],
                }

            # Make prediction
            result = self.model_loader.predict(sensor_data)

            # Add validation warnings if any
            if validation["warnings"]:
                result["warnings"] = validation["warnings"]

            return result

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def predict_from_json(self, json_data: str) -> Dict[str, Any]:
        """Make prediction from JSON string"""

        try:
            data = json.loads(json_data)
            return self.predict_single(data)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def predict_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Make predictions on data from CSV file"""

        try:
            # Load data
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df)} records from {file_path}")

            # Make batch predictions
            results = self.model_loader.predict_batch(df)

            # Add metadata
            for i, result in enumerate(results):
                result["row_index"] = i
                result["source_file"] = file_path

            return results

        except Exception as e:
            logger.error(f"File prediction error: {e}")
            return [{"error": str(e), "timestamp": datetime.now().isoformat()}]

    def predict_batch(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Make predictions on batch of sensor data"""

        results = []
        for i, data in enumerate(data_list):
            result = self.predict_single(data)
            result["batch_index"] = i
            results.append(result)

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return self.model_loader.get_model_info()


def create_sample_data() -> Dict[str, Any]:
    """Create sample sensor data for testing"""

    return {
        "Temperature[C]": 25.5,
        "Humidity[%]": 45.2,
        "TVOC[ppb]": 150.0,
        "eCO2[ppm]": 450.0,
        "Raw H2": 12500,
        "Raw Ethanol": 18500,
        "Pressure[hPa]": 1013.25,
        "PM1.0": 5.2,
        "PM2.5": 8.1,
        "NC0.5": 1200,
        "NC1.0": 800,
        "NC2.5": 150,
        "CNT": 50,
    }


def create_fire_scenario_data() -> Dict[str, Any]:
    """Create sensor data simulating fire conditions"""

    return {
        "Temperature[C]": 55.0,  # High temperature
        "Humidity[%]": 25.0,  # Low humidity
        "TVOC[ppb]": 1500.0,  # High TVOC
        "eCO2[ppm]": 1200.0,  # High CO2
        "Raw H2": 25000,  # High H2
        "Raw Ethanol": 35000,  # High Ethanol
        "Pressure[hPa]": 1010.0,
        "PM1.0": 45.0,  # High particulates
        "PM2.5": 65.0,  # High particulates
        "NC0.5": 5000,
        "NC1.0": 3500,
        "NC2.5": 800,
        "CNT": 200,
    }


def main():
    """Main function for command-line interface"""

    parser = argparse.ArgumentParser(description="IoT Smoke Detection Prediction")
    parser.add_argument("--model", type=str, help="Path to trained model file")
    parser.add_argument("--data", type=str, help="JSON string with sensor data")
    parser.add_argument("--file", type=str, help="CSV file with sensor data")
    parser.add_argument(
        "--sample", action="store_true", help="Use sample data for testing"
    )
    parser.add_argument(
        "--fire-scenario",
        action="store_true",
        help="Use fire scenario data for testing",
    )
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    parser.add_argument("--info", action="store_true", help="Show model information")

    args = parser.parse_args()

    try:
        # Initialize predictor
        predictor = SmokeDetectionPredictor(args.model)

        # Show model info if requested
        if args.info:
            model_info = predictor.get_model_info()
            print("Model Information:")
            print(json.dumps(model_info, indent=2))
            return

        results = None

        # Handle different input types
        if args.sample:
            logger.info("Using sample data for prediction")
            sample_data = create_sample_data()
            print("Sample sensor data:")
            print(json.dumps(sample_data, indent=2))
            results = predictor.predict_single(sample_data)

        elif args.fire_scenario:
            logger.info("Using fire scenario data for prediction")
            fire_data = create_fire_scenario_data()
            print("Fire scenario sensor data:")
            print(json.dumps(fire_data, indent=2))
            results = predictor.predict_single(fire_data)

        elif args.data:
            logger.info("Using provided JSON data for prediction")
            results = predictor.predict_from_json(args.data)

        elif args.file:
            logger.info(f"Using data from file: {args.file}")
            results = predictor.predict_from_file(args.file)

        else:
            # Interactive mode
            print("Interactive Prediction Mode")
            print("Enter sensor data as JSON (or 'quit' to exit):")

            while True:
                try:
                    user_input = input("> ")
                    if user_input.lower() in ["quit", "exit", "q"]:
                        break

                    if user_input.lower() == "sample":
                        user_input = json.dumps(create_sample_data())
                        print(f"Using sample data: {user_input}")
                    elif user_input.lower() == "fire":
                        user_input = json.dumps(create_fire_scenario_data())
                        print(f"Using fire scenario: {user_input}")

                    result = predictor.predict_from_json(user_input)
                    print("Prediction Result:")
                    print(json.dumps(result, indent=2))
                    print()

                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"Error: {e}")

            return

        # Display results
        if results:
            print("\nPrediction Results:")
            print(json.dumps(results, indent=2))

            # Save to file if requested
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results saved to {args.output}")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
