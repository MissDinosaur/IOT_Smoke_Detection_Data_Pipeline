"""
Model loader for IoT smoke detection inference.
Handles loading trained models and preparing them for prediction.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import pickle
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Project imports
from config.constants import TARGET_COLUMN
from config.env_config import MODEL_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("model_loader")


class SmokeDetectionModelLoader:
    """Loads and manages trained smoke detection models"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or MODEL_PATH
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.target_column = None
        self.model_info = {}
        self.is_loaded = False

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Load trained model from pickle file"""

        if model_path:
            self.model_path = model_path

        try:
            logger.info(f"Loading model from {self.model_path}")

            with open(self.model_path, "rb") as f:
                model_package = pickle.load(f)

            # Extract model components
            self.model = model_package["model"]
            self.feature_columns = model_package["feature_columns"]
            self.target_column = model_package.get("target_column", TARGET_COLUMN)
            self.scaler = model_package.get("scaler")

            # Store model info
            self.model_info = {
                "model_type": type(self.model).__name__,
                "feature_count": len(self.feature_columns),
                "has_scaler": self.scaler is not None,
                "training_timestamp": model_package.get("training_timestamp"),
                "model_name": model_package.get("model_name", "unknown"),
            }

            self.is_loaded = True

            logger.info(f"Model loaded successfully:")
            logger.info(f"  Type: {self.model_info['model_type']}")
            logger.info(f"  Features: {self.model_info['feature_count']}")
            logger.info(f"  Has Scaler: {self.model_info['has_scaler']}")

            return True

        except FileNotFoundError:
            logger.error(f"Model file not found: {self.model_path}")
            return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def prepare_features(self, data: Union[Dict[str, Any], pd.DataFrame]) -> np.ndarray:
        """Prepare input data for prediction"""

        if not self.is_loaded:
            raise ValueError("Model not loaded. Call load_model() first.")

        # Convert dict to DataFrame if needed
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        elif isinstance(data, pd.Series):
            data = pd.DataFrame([data])

        # Ensure we have all required features
        missing_features = set(self.feature_columns) - set(data.columns)
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
            # Fill missing features with default values
            for feature in missing_features:
                data[feature] = self._get_default_value(feature)

        # Select and order features
        X = data[self.feature_columns]

        # Handle missing values
        X = X.fillna(X.median())

        # Apply scaling if available
        if self.scaler is not None:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X.values

        return X_scaled

    def _get_default_value(self, feature_name: str) -> float:
        """Get default value for missing features"""

        defaults = {
            "Temperature[C]": 20.0,
            "Humidity[%]": 50.0,
            "TVOC[ppb]": 0.0,
            "eCO2[ppm]": 400.0,
            "Raw H2": 0.0,
            "Raw Ethanol": 0.0,
            "Pressure[hPa]": 1013.25,
            "PM1.0": 0.0,
            "PM2.5": 0.0,
            "NC0.5": 0.0,
            "NC1.0": 0.0,
            "NC2.5": 0.0,
            "CNT": 0,
            "Fire Alarm": 0,
        }

        # For engineered features, use 0 as default
        return defaults.get(feature_name, 0.0)

    def predict(self, data: Union[Dict[str, Any], pd.DataFrame]) -> Dict[str, Any]:
        """Make prediction on input data"""

        if not self.is_loaded:
            raise ValueError("Model not loaded. Call load_model() first.")

        try:
            # Prepare features
            X = self.prepare_features(data)

            # Make prediction
            prediction = self.model.predict(X)[0]

            # Get prediction probability if available
            probability = None
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X)[0]
                probability = {"no_fire": float(proba[0]), "fire": float(proba[1])}

            # Prepare result
            result = {
                "prediction": int(prediction),
                "prediction_label": "Fire Detected" if prediction == 1 else "No Fire",
                "probability": probability,
                "confidence": float(max(proba)) if probability else None,
                "timestamp": datetime.now().isoformat(),
                "model_info": self.model_info,
            }

            return result

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise

    def predict_batch(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Make predictions on batch of data"""

        if not self.is_loaded:
            raise ValueError("Model not loaded. Call load_model() first.")

        try:
            # Prepare features
            X = self.prepare_features(data)

            # Make predictions
            predictions = self.model.predict(X)

            # Get prediction probabilities if available
            probabilities = None
            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(X)

            # Prepare results
            results = []
            for i, pred in enumerate(predictions):
                result = {
                    "prediction": int(pred),
                    "prediction_label": "Fire Detected" if pred == 1 else "No Fire",
                    "probability": (
                        {
                            "no_fire": float(probabilities[i][0]),
                            "fire": float(probabilities[i][1]),
                        }
                        if probabilities is not None
                        else None
                    ),
                    "confidence": (
                        float(max(probabilities[i]))
                        if probabilities is not None
                        else None
                    ),
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""

        if not self.is_loaded:
            return {"error": "Model not loaded"}

        return self.model_info.copy()

    def validate_input(
        self, data: Union[Dict[str, Any], pd.DataFrame]
    ) -> Dict[str, Any]:
        """Validate input data for prediction"""

        validation_result = {"is_valid": True, "errors": [], "warnings": []}

        # Convert to DataFrame for easier validation
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            df = data

        # Check for required features
        missing_features = set(self.feature_columns) - set(df.columns)
        if missing_features:
            validation_result["warnings"].append(
                f"Missing features will use defaults: {list(missing_features)}"
            )

        # Check data types and ranges
        numeric_features = [
            "Temperature[C]",
            "Humidity[%]",
            "TVOC[ppb]",
            "eCO2[ppm]",
            "Raw H2",
            "Raw Ethanol",
            "Pressure[hPa]",
            "PM1.0",
            "PM2.5",
            "NC0.5",
            "NC1.0",
            "NC2.5",
            "CNT",
        ]

        for feature in numeric_features:
            if feature in df.columns:
                try:
                    pd.to_numeric(df[feature])
                except ValueError:
                    validation_result["errors"].append(
                        f"Non-numeric values in {feature}"
                    )
                    validation_result["is_valid"] = False

        return validation_result


# Global model loader instance
_model_loader = None


def get_model_loader(model_path: Optional[str] = None) -> SmokeDetectionModelLoader:
    """Get global model loader instance"""
    global _model_loader

    if _model_loader is None or model_path:
        _model_loader = SmokeDetectionModelLoader(model_path)
        if not _model_loader.load_model():
            logger.warning("Failed to load model on initialization")

    return _model_loader


def load_model(model_path: Optional[str] = None) -> SmokeDetectionModelLoader:
    """Load model and return loader instance"""
    loader = SmokeDetectionModelLoader(model_path)
    if loader.load_model():
        return loader
    else:
        raise ValueError(f"Failed to load model from {model_path}")


if __name__ == "__main__":
    # Test model loading
    try:
        loader = get_model_loader()
        if loader.is_loaded:
            logger.info("Model loaded successfully for testing")
            print(f"Model info: {loader.get_model_info()}")
        else:
            logger.warning("Model not loaded - check model path")
    except Exception as e:
        logger.error(f"Error testing model loader: {e}")
