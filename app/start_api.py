#!/usr/bin/env python3
"""
Flask API startup script with model availability checking.

This script ensures the ML model is available before starting the Flask API.
It handles model waiting, fallback creation, and proper startup sequencing.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
sys.path.append(str(project_root))

from config.env_config import MODEL_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_model(max_wait_minutes=30, check_interval=30):
    """Wait for ML model to be available."""
    model_path = Path(MODEL_PATH)
    max_wait_seconds = max_wait_minutes * 60
    start_time = time.time()
    
    logger.info(f"Waiting for ML model at {model_path}")
    logger.info(f"Will wait up to {max_wait_minutes} minutes...")
    
    while time.time() - start_time < max_wait_seconds:
        if model_path.exists():
            logger.info(f"✅ Model found at {model_path}")
            return True
        
        # Check for models in ml/models directory
        ml_models_dir = Path("ml/models")
        if ml_models_dir.exists():
            model_files = list(ml_models_dir.glob("*.pkl"))
            if model_files:
                logger.info(f"Found {len(model_files)} model files in ml/models/")
                # Try to copy the latest one
                try:
                    latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
                    logger.info(f"Copying latest model: {latest_model}")
                    
                    # Create directory if needed
                    model_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy model
                    import shutil
                    shutil.copy2(latest_model, model_path)
                    logger.info(f"✅ Model copied to {model_path}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to copy model: {e}")
        
        elapsed_minutes = (time.time() - start_time) / 60
        logger.info(f"⏳ Waiting for model... ({elapsed_minutes:.1f}/{max_wait_minutes} minutes)")
        time.sleep(check_interval)
    
    logger.warning(f"❌ Model not found after {max_wait_minutes} minutes")
    return False


def create_placeholder_model():
    """Create a placeholder model for testing."""
    logger.info("Creating placeholder model for testing...")
    
    try:
        # Import the model creation function
        from ml.training.ensure_model_exists import create_placeholder_model as create_placeholder
        return create_placeholder()
    except Exception as e:
        logger.error(f"Failed to create placeholder model: {e}")
        return False


def start_flask_api():
    """Start the Flask API."""
    logger.info("Starting Flask API...")
    
    try:
        # Import and run the Flask app
        from app.api.prediction_api import create_app
        
        app = create_app()
        
        # Get configuration
        host = os.getenv("FLASK_HOST", "0.0.0.0")
        port = int(os.getenv("FLASK_PORT", "5000"))
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
        
        logger.info(f"🚀 Starting Flask API on {host}:{port}")
        logger.info(f"📁 Model path: {MODEL_PATH}")
        logger.info(f"🐛 Debug mode: {debug}")
        
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start Flask API: {e}")
        raise


def main():
    """Main startup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="IoT Smoke Detection API Startup")
    parser.add_argument("--wait-for-model", action="store_true", 
                       help="Wait for ML model to be available")
    parser.add_argument("--max-wait-minutes", type=int, default=30,
                       help="Maximum minutes to wait for model")
    parser.add_argument("--create-placeholder", action="store_true",
                       help="Create placeholder model if real model not found")
    parser.add_argument("--skip-model-check", action="store_true",
                       help="Skip model availability check")
    
    args = parser.parse_args()
    
    logger.info("🔥 IoT Smoke Detection API - Starting Up")
    logger.info("=" * 50)
    
    # Check model availability
    if not args.skip_model_check:
        model_path = Path(MODEL_PATH)
        
        if not model_path.exists():
            if args.wait_for_model:
                logger.info("Model not found, waiting for training to complete...")
                if not wait_for_model(max_wait_minutes=args.max_wait_minutes):
                    if args.create_placeholder:
                        logger.info("Creating placeholder model for testing...")
                        if not create_placeholder_model():
                            logger.error("Failed to create placeholder model")
                            sys.exit(1)
                    else:
                        logger.error("Model not available and no placeholder requested")
                        logger.info("Use --create-placeholder to create a test model")
                        sys.exit(1)
            else:
                logger.warning("Model not found and not waiting")
                if args.create_placeholder:
                    if not create_placeholder_model():
                        logger.error("Failed to create placeholder model")
                        sys.exit(1)
                else:
                    logger.warning("API will start but may have limited functionality")
        else:
            logger.info(f"✅ Model found at {model_path}")
    else:
        logger.info("Skipping model availability check")
    
    # Start Flask API
    try:
        start_flask_api()
    except KeyboardInterrupt:
        logger.info("🛑 API shutdown requested")
    except Exception as e:
        logger.error(f"💥 API startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
