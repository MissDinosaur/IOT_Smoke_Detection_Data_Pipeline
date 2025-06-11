#!/usr/bin/env python3
"""
Generate initial ML model for IoT smoke detection.

This script creates an initial trained model if none exists,
ensuring the system can start up properly.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

from ml.training.train_model import train_smoke_detection_model, TrainingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("initial_model_generator")


def generate_initial_model():
    """Generate initial model if none exists."""
    
    # Define paths
    models_dir = Path("ml/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    best_model_path = models_dir / "best_model.pkl"
    data_path = "data/smoke_detection_iot.csv"
    
    # Check if model already exists
    if best_model_path.exists():
        logger.info(f"✅ Model already exists: {best_model_path}")
        return str(best_model_path)
    
    # Check if data exists
    if not Path(data_path).exists():
        logger.error(f"❌ Training data not found: {data_path}")
        return None
    
    try:
        logger.info("🤖 Generating initial ML model...")
        
        # Configure training for quick initial model
        config = TrainingConfig(
            random_state=42,
            test_size=0.2,
            use_feature_engineering=True,
            save_plots=False  # Skip plots for initial generation
        )
        
        # Train model
        trainer, results = train_smoke_detection_model(
            data_path=data_path,
            config=config
        )
        
        # Save as best model
        trainer.save_model(str(best_model_path))
        logger.info(f"✅ Initial model saved: {best_model_path}")
        
        # Log basic results
        if trainer.best_model_name and results:
            best_result = results.get(trainer.best_model_name, {})
            metrics = best_result.get('metrics', {})
            logger.info(f"🎯 Model Performance:")
            logger.info(f"   Algorithm: {trainer.best_model_name}")
            logger.info(f"   Accuracy: {metrics.get('accuracy', 0):.3f}")
            logger.info(f"   F1-Score: {metrics.get('f1', 0):.3f}")
        
        return str(best_model_path)
        
    except Exception as e:
        logger.error(f"❌ Error generating initial model: {e}")
        return None


if __name__ == "__main__":
    model_path = generate_initial_model()
    if model_path:
        print(f"SUCCESS: Model generated at {model_path}")
        sys.exit(0)
    else:
        print("FAILED: Could not generate initial model")
        sys.exit(1)
