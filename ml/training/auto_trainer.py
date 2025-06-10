#!/usr/bin/env python3
"""
Automatic ML Model Training Service.

This service automatically trains ML models when the container starts
and periodically retrains them based on new data.

Features:
- Automatic model training on startup
- Periodic retraining (configurable)
- Model validation and deployment
- Training metrics logging
- Model versioning
"""

import os
import sys
import time
import schedule
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

from ml.training.train_model import train_smoke_detection_model, TrainingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/app/logs/ml_training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_trainer")


class AutoMLTrainer:
    """Automatic ML model training service."""
    
    def __init__(self):
        self.data_path = "/app/data/smoke_detection_iot.csv"
        self.models_dir = Path("/app/ml/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.training_interval_hours = int(os.getenv("ML_TRAINING_INTERVAL_HOURS", "24"))
        self.auto_train_on_startup = os.getenv("ML_AUTO_TRAIN_ON_STARTUP", "true").lower() == "true"
        
    def check_data_availability(self) -> bool:
        """Check if training data is available."""
        if not Path(self.data_path).exists():
            logger.warning(f"Training data not found: {self.data_path}")
            return False
        
        # Check file size
        file_size = Path(self.data_path).stat().st_size
        if file_size < 1024:  # Less than 1KB
            logger.warning(f"Training data file too small: {file_size} bytes")
            return False
        
        logger.info(f"Training data available: {self.data_path} ({file_size} bytes)")
        return True
    
    def train_model(self) -> bool:
        """Train ML model and save to models directory."""
        try:
            logger.info("🤖 Starting automatic ML model training...")
            
            # Check data availability
            if not self.check_data_availability():
                logger.error("❌ Cannot train model - data not available")
                return False
            
            # Configure training
            config = TrainingConfig(
                random_state=42,
                test_size=0.2,
                use_feature_engineering=True
            )
            
            # Train model
            trainer, results = train_smoke_detection_model(
                data_path=self.data_path,
                config=config
            )
            
            # Save model with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = self.models_dir / f"model_{timestamp}.pkl"
            best_model_path = self.models_dir / "best_model.pkl"
            
            # Save timestamped version
            trainer.save_model(str(model_path))
            logger.info(f"✅ Model saved: {model_path}")
            
            # Save as best model (for production use)
            trainer.save_model(str(best_model_path))
            logger.info(f"✅ Best model updated: {best_model_path}")
            
            # Log training results
            best_model_info = results.get("best_model", {})
            logger.info(f"🎯 Training Results:")
            logger.info(f"   Best Model: {best_model_info.get('name', 'Unknown')}")
            logger.info(f"   Accuracy: {best_model_info.get('accuracy', 0):.3f}")
            logger.info(f"   Precision: {best_model_info.get('precision', 0):.3f}")
            logger.info(f"   Recall: {best_model_info.get('recall', 0):.3f}")
            logger.info(f"   F1-Score: {best_model_info.get('f1', 0):.3f}")
            
            # Clean up old models (keep last 5)
            self.cleanup_old_models()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during model training: {e}")
            return False
    
    def cleanup_old_models(self):
        """Clean up old model files, keeping the most recent ones."""
        try:
            # Get all timestamped model files
            model_files = list(self.models_dir.glob("model_*.pkl"))
            model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep the 5 most recent models
            models_to_keep = 5
            if len(model_files) > models_to_keep:
                for old_model in model_files[models_to_keep:]:
                    old_model.unlink()
                    logger.info(f"🗑️ Cleaned up old model: {old_model.name}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Error during model cleanup: {e}")
    
    def check_model_exists(self) -> bool:
        """Check if a trained model already exists."""
        best_model_path = self.models_dir / "best_model.pkl"
        return best_model_path.exists()
    
    def schedule_training(self):
        """Schedule periodic model retraining."""
        logger.info(f"📅 Scheduling model retraining every {self.training_interval_hours} hours")
        schedule.every(self.training_interval_hours).hours.do(self.train_model)
    
    def run(self):
        """Main training service loop."""
        logger.info("🚀 Starting Auto ML Training Service")
        
        # Train model on startup if enabled and no model exists
        if self.auto_train_on_startup:
            if not self.check_model_exists():
                logger.info("🎯 No existing model found - training initial model")
                self.train_model()
            else:
                logger.info("✅ Existing model found - skipping initial training")
        else:
            logger.info("⏭️ Auto-training on startup disabled")
        
        # Schedule periodic retraining
        self.schedule_training()
        
        # Main service loop
        logger.info("🔄 Starting training scheduler loop")
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("👋 Training service interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in training service loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying


def main():
    """Main entry point for auto trainer."""
    trainer = AutoMLTrainer()
    trainer.run()


if __name__ == "__main__":
    main()
