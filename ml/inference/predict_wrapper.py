"""
Flask API wrapper for IoT smoke detection predictions.
Provides REST API endpoints for real-time smoke detection inference.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

# Project imports
from ml.inference.model_loader import get_model_loader
from ml.inference.predict import SmokeDetectionPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("prediction_api")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global predictor instance
predictor = None


def initialize_predictor(model_path: Optional[str] = None):
    """Initialize the global predictor instance"""
    global predictor
    try:
        predictor = SmokeDetectionPredictor(model_path)
        logger.info("Predictor initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize predictor: {e}")
        return False


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "model_loaded": predictor is not None and predictor.model_loader.is_loaded,
        }
    )


@app.route("/model/info", methods=["GET"])
def get_model_info():
    """Get information about the loaded model"""
    if predictor is None:
        return jsonify({"error": "Predictor not initialized"}), 500

    try:
        model_info = predictor.get_model_info()
        return jsonify(model_info)
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/predict", methods=["POST"])
def predict_single():
    """Make prediction on single sensor reading"""
    if predictor is None:
        return jsonify({"error": "Predictor not initialized"}), 500

    try:
        # Get JSON data from request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        sensor_data = request.get_json()

        if not sensor_data:
            return jsonify({"error": "No data provided"}), 400

        # Make prediction
        result = predictor.predict_single(sensor_data)

        # Log prediction request
        logger.info(f"Prediction request: {result.get('prediction_label', 'Unknown')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/predict/batch", methods=["POST"])
def predict_batch():
    """Make predictions on batch of sensor readings"""
    if predictor is None:
        return jsonify({"error": "Predictor not initialized"}), 500

    try:
        # Get JSON data from request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Expect list of sensor readings
        if not isinstance(data, list):
            return jsonify({"error": "Data must be a list of sensor readings"}), 400

        # Make batch predictions
        results = predictor.predict_batch(data)

        # Log batch prediction request
        fire_count = sum(1 for r in results if r.get("prediction") == 1)
        logger.info(
            f"Batch prediction: {len(results)} samples, {fire_count} fire detections"
        )

        return jsonify(
            {
                "predictions": results,
                "summary": {
                    "total_samples": len(results),
                    "fire_detections": fire_count,
                    "no_fire_detections": len(results) - fire_count,
                },
            }
        )

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/predict/sample", methods=["GET"])
def predict_sample():
    """Make prediction using sample data"""
    if predictor is None:
        return jsonify({"error": "Predictor not initialized"}), 500

    try:
        from ml.inference.predict import create_sample_data

        sample_data = create_sample_data()
        result = predictor.predict_single(sample_data)

        return jsonify({"input_data": sample_data, "prediction": result})

    except Exception as e:
        logger.error(f"Sample prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/predict/fire-scenario", methods=["GET"])
def predict_fire_scenario():
    """Make prediction using fire scenario data"""
    if predictor is None:
        return jsonify({"error": "Predictor not initialized"}), 500

    try:
        from ml.inference.predict import create_fire_scenario_data

        fire_data = create_fire_scenario_data()
        result = predictor.predict_single(fire_data)

        return jsonify({"input_data": fire_data, "prediction": result})

    except Exception as e:
        logger.error(f"Fire scenario prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validate", methods=["POST"])
def validate_input():
    """Validate sensor data input"""
    if predictor is None:
        return jsonify({"error": "Predictor not initialized"}), 500

    try:
        # Get JSON data from request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        sensor_data = request.get_json()

        if not sensor_data:
            return jsonify({"error": "No data provided"}), 400

        # Validate input
        validation_result = predictor.model_loader.validate_input(sensor_data)

        return jsonify(validation_result)

    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


def create_app(model_path: Optional[str] = None):
    """Create and configure Flask app"""

    # Initialize predictor
    if not initialize_predictor(model_path):
        logger.warning(
            "Failed to initialize predictor - API will have limited functionality"
        )

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Smoke Detection Prediction API")
    parser.add_argument("--model", type=str, help="Path to trained model file")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Create app
    app = create_app(args.model)

    # Run app
    logger.info(f"Starting Smoke Detection API on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
