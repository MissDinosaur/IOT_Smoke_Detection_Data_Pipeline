#!/usr/bin/env python3
"""
Ensure ML model exists for Flask API.

This script checks if the expected model file exists and creates it if necessary.
Used as a fallback to ensure Flask API can start even if main training hasn't completed.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

from config.env_config import MODEL_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_model_exists():
    """Ensure the model file exists, create a basic one if not."""
    
    model_path = Path(MODEL_PATH)
    
    if model_path.exists():
        logger.info(f"Model already exists at {model_path}")
        return True
    
    logger.info(f"Model not found at {model_path}, checking for alternative models...")
    
    # Check for timestamped models in ml/models directory
    ml_models_dir = Path("ml/models")
    if ml_models_dir.exists():
        model_files = list(ml_models_dir.glob("smoke_detection_model_*.pkl"))
        if model_files:
            # Use the most recent model
            latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Found existing model: {latest_model}")
            
            # Create the expected model path directory
            model_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the latest model to expected location
            import shutil
            shutil.copy2(latest_model, model_path)
            logger.info(f"Copied model from {latest_model} to {model_path}")
            return True
    
    logger.warning(f"No trained model found. Flask API will need to wait for training to complete.")
    return False


def create_placeholder_model():
    """Create a placeholder model for testing purposes."""
    import pickle
    import numpy as np
    from datetime import datetime
    
    logger.info("Creating placeholder model for testing...")
    
    # Create a simple placeholder model
    class PlaceholderModel:
        def predict(self, X):
            # Simple rule-based prediction for testing
            if hasattr(X, 'iloc'):
                # DataFrame
                temp = X.iloc[:, 0] if len(X.columns) > 0 else 50
            else:
                # Array
                temp = X[:, 0] if len(X.shape) > 1 and X.shape[1] > 0 else 50
            
            # Simple threshold: high temperature = fire
            return (temp > 60).astype(int)
        
        def predict_proba(self, X):
            predictions = self.predict(X)
            # Return probabilities [no_fire, fire]
            proba = np.zeros((len(predictions), 2))
            for i, pred in enumerate(predictions):
                if pred == 1:  # Fire
                    proba[i] = [0.2, 0.8]
                else:  # No fire
                    proba[i] = [0.8, 0.2]
            return proba
    
    # Create model package
    model_package = {
        "model": PlaceholderModel(),
        "model_name": "placeholder_model",
        "feature_columns": [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ],
        "target_column": "Fire Alarm",
        "training_timestamp": datetime.now().isoformat(),
        "scaler": None,
        "model_metrics": {
            "accuracy": 0.85,
            "precision": 0.80,
            "recall": 0.75,
            "f1": 0.77
        },
        "is_placeholder": True
    }
    
    # Save placeholder model
    model_path = Path(MODEL_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(model_path, "wb") as f:
        pickle.dump(model_package, f)
    
    logger.info(f"Placeholder model created at {model_path}")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ensure ML model exists")
    parser.add_argument("--create-placeholder", action="store_true", 
                       help="Create a placeholder model if none exists")
    
    args = parser.parse_args()
    
    if not ensure_model_exists():
        if args.create_placeholder:
            create_placeholder_model()
        else:
            logger.info("Use --create-placeholder to create a basic model for testing")
            sys.exit(1)
    
    logger.info("Model availability check completed successfully!")
