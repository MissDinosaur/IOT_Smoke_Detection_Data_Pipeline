"""
Flask API for IoT Smoke Detection Predictions.

This module provides a comprehensive REST API for smoke detection predictions
that interacts with ML models via pickle files.

Features:
- Real-time single and batch predictions
- Model information and health checks
- Data validation endpoints
- Prometheus metrics integration
- Automatic model loading from pickle files
- Sample data testing endpoints

Endpoints:
- POST /predict - Single prediction
- POST /predict/batch - Batch predictions
- GET /predict/sample - Test with sample data
- GET /predict/fire-scenario - Fire scenario test
- GET /model/info - Model metadata
- GET /health - Health check
- POST /validate - Data validation
- GET /metrics - Prometheus metrics
"""

import sys
import os
import pickle
import logging
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
import pandas as pd
import numpy as np

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("prediction_api")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global model storage
model_cache = {
    "model": None,
    "scaler": None,
    "feature_columns": None,
    "model_info": None,
    "last_loaded": None,
}

# Prometheus metrics
REQUEST_COUNT = Counter(
    "smoke_api_requests_total", "Total API requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "smoke_api_request_duration_seconds", "Request duration", ["method", "endpoint"]
)
PREDICTION_COUNT = Counter(
    "smoke_api_predictions_total", "Total predictions", ["prediction_type", "result"]
)
MODEL_INFO = Gauge(
    "smoke_api_model_info", "Model information", ["model_version", "model_type"]
)
SENSOR_READINGS = Gauge(
    "smoke_api_sensor_readings", "Latest sensor readings", ["sensor_type"]
)
ERROR_COUNT = Counter("smoke_api_errors_total", "Total errors", ["error_type"])
PROCESSING_TIME = Histogram(
    "smoke_api_processing_time_seconds", "Processing time for predictions"
)

# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "ml/models/best_model.pkl")
MODEL_RELOAD_INTERVAL = int(os.getenv("MODEL_RELOAD_INTERVAL", "3600"))  # 1 hour

# API Configuration
API_CONFIG = {
    "version": "1.0.0",
    "model_reload_interval": MODEL_RELOAD_INTERVAL,
    "max_batch_size": 1000,
    "supported_formats": ["json"],
    "cors_enabled": True,
    "metrics_enabled": True,
}

# Sensor schema and validation rules
SENSOR_SCHEMA = {
    "required_fields": [
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
    ],
    "field_types": {
        "Temperature[C]": {"type": "float", "unit": "Celsius", "range": [-40, 125]},
        "Humidity[%]": {"type": "float", "unit": "Percentage", "range": [0, 100]},
        "TVOC[ppb]": {"type": "float", "unit": "ppb", "range": [0, 60000]},
        "eCO2[ppm]": {"type": "float", "unit": "ppm", "range": [400, 8192]},
        "Raw H2": {"type": "float", "unit": "raw", "range": [0, 65535]},
        "Raw Ethanol": {"type": "float", "unit": "raw", "range": [0, 65535]},
        "Pressure[hPa]": {"type": "float", "unit": "hPa", "range": [300, 1100]},
        "PM1.0": {"type": "float", "unit": "μg/m³", "range": [0, 1000]},
        "PM2.5": {"type": "float", "unit": "μg/m³", "range": [0, 1000]},
        "NC0.5": {"type": "float", "unit": "#/cm³", "range": [0, 10000]},
        "NC1.0": {"type": "float", "unit": "#/cm³", "range": [0, 10000]},
        "NC2.5": {"type": "float", "unit": "#/cm³", "range": [0, 10000]},
    },
    "validation_rules": {
        "all_fields_required": True,
        "numeric_values_only": True,
        "range_validation": True,
        "null_values_allowed": False,
    },
}

# Global statistics tracking
prediction_stats = {
    "total_predictions": 0,
    "fire_predictions": 0,
    "no_fire_predictions": 0,
    "batch_predictions": 0,
    "average_confidence": 0.0,
    "average_processing_time": 0.0,
    "last_reset": time.time(),
}


def load_model_from_pickle(model_path: str = None) -> bool:
    """Load ML model from pickle file."""
    global model_cache

    if model_path is None:
        model_path = MODEL_PATH

    try:
        # Check if file exists
        if not Path(model_path).exists():
            logger.warning(f"Model file not found: {model_path}")
            return False

        # Check if we need to reload
        file_mtime = Path(model_path).stat().st_mtime
        if (
            model_cache["last_loaded"]
            and file_mtime <= model_cache["last_loaded"]
            and model_cache["model"] is not None
        ):
            return True  # Model is already loaded and up to date

        logger.info(f"Loading model from {model_path}")

        # Load pickle file
        with open(model_path, "rb") as f:
            model_package = pickle.load(f)

        # Extract components
        model_cache["model"] = model_package.get("model")
        model_cache["scaler"] = model_package.get("scaler")
        model_cache["feature_columns"] = model_package.get("feature_columns", [])
        model_cache["last_loaded"] = time.time()

        # Create model info
        model_cache["model_info"] = {
            "model_type": type(model_cache["model"]).__name__,
            "algorithm": model_package.get("model_name", "unknown"),
            "feature_count": len(model_cache["feature_columns"]),
            "training_timestamp": model_package.get("training_timestamp"),
            "version": model_package.get("version", "1.0"),
            "loaded_at": datetime.now().isoformat(),
        }

        # Update Prometheus metrics
        MODEL_INFO.labels(
            model_version=model_cache["model_info"]["version"],
            model_type=model_cache["model_info"]["model_type"],
        ).set(1)

        logger.info(
            f"✅ Model loaded successfully: {model_cache['model_info']['algorithm']}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Error loading model: {e}")
        ERROR_COUNT.labels(error_type="model_loading_error").inc()
        return False


def ensure_model_loaded() -> bool:
    """Ensure model is loaded, load if necessary."""
    if model_cache["model"] is None:
        return load_model_from_pickle()

    # Check if we should reload (every hour)
    if (time.time() - model_cache.get("last_loaded", 0)) > MODEL_RELOAD_INTERVAL:
        logger.info("Checking for model updates...")
        load_model_from_pickle()

    return model_cache["model"] is not None


def validate_sensor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate incoming sensor data."""
    validation_result = {"valid": True, "errors": [], "warnings": []}

    # Check if model is loaded
    if not ensure_model_loaded():
        validation_result["valid"] = False
        validation_result["errors"].append("Model not available")
        return validation_result

    # Check required fields
    feature_columns = model_cache["feature_columns"]
    missing_fields = [col for col in feature_columns if col not in data]

    if missing_fields:
        validation_result["valid"] = False
        validation_result["errors"].append(f"Missing required fields: {missing_fields}")

    # Check data types and ranges
    for key, value in data.items():
        if key in feature_columns:
            if not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    validation_result["errors"].append(
                        f"Invalid data type for {key}: {type(value)}"
                    )
                    validation_result["valid"] = False

    return validation_result


def prepare_features(data: Dict[str, Any]) -> Optional[np.ndarray]:
    """Prepare features for prediction."""
    try:
        if not ensure_model_loaded():
            return None

        feature_columns = model_cache["feature_columns"]

        # Create feature vector
        features = []
        for col in feature_columns:
            value = data.get(col, 0.0)  # Default to 0 if missing
            features.append(float(value))

        # Convert to numpy array
        feature_array = np.array(features).reshape(1, -1)

        # Apply scaling if available
        if model_cache["scaler"] is not None:
            feature_array = model_cache["scaler"].transform(feature_array)

        return feature_array

    except Exception as e:
        logger.error(f"Error preparing features: {e}")
        return None


def update_prediction_stats(
    prediction_result: str, confidence: Dict[str, float], processing_time: float
):
    """Update global prediction statistics."""
    global prediction_stats

    prediction_stats["total_predictions"] += 1

    if prediction_result == "fire":
        prediction_stats["fire_predictions"] += 1
    else:
        prediction_stats["no_fire_predictions"] += 1

    # Update running averages
    total = prediction_stats["total_predictions"]

    # Update average confidence (fire confidence)
    fire_confidence = confidence.get("fire", 0.0) if confidence else 0.0
    prediction_stats["average_confidence"] = (
        prediction_stats["average_confidence"] * (total - 1) + fire_confidence
    ) / total

    # Update average processing time
    prediction_stats["average_processing_time"] = (
        prediction_stats["average_processing_time"] * (total - 1) + processing_time
    ) / total


def track_metrics(f):
    """Decorator to track request metrics."""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        endpoint = request.endpoint or "unknown"
        method = request.method

        try:
            result = f(*args, **kwargs)

            # Track successful request
            status = "200" if not isinstance(result, tuple) else str(result[1])
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()

            # Track duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            return result

        except Exception as e:
            # Track error
            ERROR_COUNT.labels(error_type=type(e).__name__).inc()
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status="500").inc()

            # Track duration even for errors
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            raise

    wrapper.__name__ = f.__name__
    return wrapper


# API Endpoints


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/health", methods=["GET"])
@track_metrics
def health_check():
    """Health check endpoint."""
    model_loaded = ensure_model_loaded()

    return jsonify(
        {
            "status": "healthy" if model_loaded else "degraded",
            "timestamp": datetime.now().isoformat(),
            "model_loaded": model_loaded,
            "model_path": MODEL_PATH,
            "uptime_seconds": (
                time.time() - app.start_time if hasattr(app, "start_time") else 0
            ),
        }
    )


@app.route("/model/info", methods=["GET"])
@track_metrics
def get_model_info():
    """Get information about the loaded model."""
    if not ensure_model_loaded():
        ERROR_COUNT.labels(error_type="model_not_available").inc()
        return jsonify({"error": "Model not available"}), 500

    return jsonify(model_cache["model_info"])


@app.route("/validate", methods=["POST"])
@track_metrics
def validate_input():
    """Validate sensor data input."""
    try:
        if not request.is_json:
            ERROR_COUNT.labels(error_type="invalid_content_type").inc()
            return jsonify({"error": "Request must be JSON"}), 400

        sensor_data = request.get_json()
        if not sensor_data:
            ERROR_COUNT.labels(error_type="no_data_provided").inc()
            return jsonify({"error": "No data provided"}), 400

        validation_result = validate_sensor_data(sensor_data)
        return jsonify(validation_result)

    except Exception as e:
        logger.error(f"Validation error: {e}")
        ERROR_COUNT.labels(error_type="validation_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/predict", methods=["POST"])
@track_metrics
def predict_single():
    """Make prediction on single sensor reading."""
    try:
        if not request.is_json:
            ERROR_COUNT.labels(error_type="invalid_content_type").inc()
            return jsonify({"error": "Request must be JSON"}), 400

        sensor_data = request.get_json()
        if not sensor_data:
            ERROR_COUNT.labels(error_type="no_data_provided").inc()
            return jsonify({"error": "No data provided"}), 400

        # Validate input
        validation = validate_sensor_data(sensor_data)
        if not validation["valid"]:
            ERROR_COUNT.labels(error_type="invalid_input_data").inc()
            return jsonify({"error": "Invalid input data", "details": validation}), 400

        # Track sensor readings
        for key, value in sensor_data.items():
            if isinstance(value, (int, float)):
                SENSOR_READINGS.labels(sensor_type=key).set(value)

        # Prepare features
        features = prepare_features(sensor_data)
        if features is None:
            ERROR_COUNT.labels(error_type="feature_preparation_error").inc()
            return jsonify({"error": "Error preparing features"}), 500

        # Make prediction
        start_time = time.time()
        model = model_cache["model"]

        prediction = model.predict(features)[0]
        prediction_proba = None

        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(features)[0]
            prediction_proba = {"no_fire": float(proba[0]), "fire": float(proba[1])}

        processing_time = time.time() - start_time

        # Track metrics
        PROCESSING_TIME.observe(processing_time)
        prediction_result = "fire" if prediction == 1 else "no_fire"
        PREDICTION_COUNT.labels(
            prediction_type="single", result=prediction_result
        ).inc()

        # Update statistics
        update_prediction_stats(prediction_result, prediction_proba, processing_time)

        # Prepare response
        result = {
            "prediction": int(prediction),
            "prediction_label": prediction_result,
            "confidence": prediction_proba,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat(),
            "model_info": {
                "algorithm": model_cache["model_info"]["algorithm"],
                "version": model_cache["model_info"]["version"],
            },
        }

        logger.info(f"Prediction: {prediction_result} (took {processing_time:.3f}s)")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        ERROR_COUNT.labels(error_type="prediction_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/predict/batch", methods=["POST"])
@track_metrics
def predict_batch():
    """Make predictions on batch of sensor readings."""
    try:
        if not request.is_json:
            ERROR_COUNT.labels(error_type="invalid_content_type").inc()
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data or not isinstance(data, list):
            ERROR_COUNT.labels(error_type="invalid_batch_data").inc()
            return jsonify({"error": "Data must be a list of sensor readings"}), 400

        results = []
        fire_count = 0

        start_time = time.time()

        for i, sensor_data in enumerate(data):
            try:
                # Validate input
                validation = validate_sensor_data(sensor_data)
                if not validation["valid"]:
                    results.append(
                        {
                            "index": i,
                            "error": "Invalid input data",
                            "details": validation,
                        }
                    )
                    continue

                # Prepare features and predict
                features = prepare_features(sensor_data)
                if features is None:
                    results.append({"index": i, "error": "Error preparing features"})
                    continue

                model = model_cache["model"]
                prediction = model.predict(features)[0]

                prediction_proba = None
                if hasattr(model, "predict_proba"):
                    proba = model.predict_proba(features)[0]
                    prediction_proba = {
                        "no_fire": float(proba[0]),
                        "fire": float(proba[1]),
                    }

                prediction_result = "fire" if prediction == 1 else "no_fire"
                if prediction == 1:
                    fire_count += 1

                results.append(
                    {
                        "index": i,
                        "prediction": int(prediction),
                        "prediction_label": prediction_result,
                        "confidence": prediction_proba,
                    }
                )

            except Exception as e:
                results.append({"index": i, "error": str(e)})

        processing_time = time.time() - start_time

        # Track metrics
        PROCESSING_TIME.observe(processing_time)
        PREDICTION_COUNT.labels(prediction_type="batch", result="mixed").inc()

        response = {
            "predictions": results,
            "summary": {
                "total_samples": len(data),
                "successful_predictions": len(
                    [r for r in results if "prediction" in r]
                ),
                "fire_detections": fire_count,
                "no_fire_detections": len(
                    [r for r in results if r.get("prediction_label") == "no_fire"]
                ),
                "errors": len([r for r in results if "error" in r]),
            },
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"Batch prediction: {len(data)} samples, {fire_count} fire detections (took {processing_time:.3f}s)"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        ERROR_COUNT.labels(error_type="batch_prediction_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/predict/sample", methods=["GET"])
@track_metrics
def predict_sample():
    """Make prediction using sample data."""
    try:
        # Create sample sensor data
        sample_data = {
            "Temperature[C]": 25.5,
            "Humidity[%]": 45.0,
            "TVOC[ppb]": 150.0,
            "eCO2[ppm]": 400.0,
            "Raw H2": 13000.0,
            "Raw Ethanol": 18500.0,
            "Pressure[hPa]": 1013.25,
            "PM1.0": 10.0,
            "PM2.5": 15.0,
            "NC0.5": 100.0,
            "NC1.0": 80.0,
            "NC2.5": 20.0,
        }

        # Make prediction
        validation = validate_sensor_data(sample_data)
        if not validation["valid"]:
            return (
                jsonify(
                    {"error": "Sample data validation failed", "details": validation}
                ),
                500,
            )

        features = prepare_features(sample_data)
        if features is None:
            return jsonify({"error": "Error preparing sample features"}), 500

        model = model_cache["model"]
        prediction = model.predict(features)[0]

        prediction_proba = None
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(features)[0]
            prediction_proba = {"no_fire": float(proba[0]), "fire": float(proba[1])}

        prediction_result = "fire" if prediction == 1 else "no_fire"
        PREDICTION_COUNT.labels(
            prediction_type="sample", result=prediction_result
        ).inc()

        result = {
            "input_data": sample_data,
            "prediction": {
                "prediction": int(prediction),
                "prediction_label": prediction_result,
                "confidence": prediction_proba,
                "timestamp": datetime.now().isoformat(),
            },
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Sample prediction error: {e}")
        ERROR_COUNT.labels(error_type="sample_prediction_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/predict/fire-scenario", methods=["GET"])
@track_metrics
def predict_fire_scenario():
    """Make prediction using fire scenario data."""
    try:
        # Create fire scenario data (high temperature, smoke particles, etc.)
        fire_scenario_data = {
            "Temperature[C]": 85.0,  # High temperature
            "Humidity[%]": 20.0,  # Low humidity (dry conditions)
            "TVOC[ppb]": 2500.0,  # High volatile organic compounds
            "eCO2[ppm]": 1200.0,  # High CO2
            "Raw H2": 25000.0,  # High hydrogen (combustion)
            "Raw Ethanol": 35000.0,  # High ethanol (combustion)
            "Pressure[hPa]": 1010.0,  # Slightly low pressure
            "PM1.0": 150.0,  # High particulate matter
            "PM2.5": 250.0,  # Very high fine particles
            "NC0.5": 2000.0,  # High particle count
            "NC1.0": 1500.0,  # High particle count
            "NC2.5": 800.0,  # High particle count
        }

        # Make prediction
        validation = validate_sensor_data(fire_scenario_data)
        if not validation["valid"]:
            return (
                jsonify(
                    {
                        "error": "Fire scenario data validation failed",
                        "details": validation,
                    }
                ),
                500,
            )

        features = prepare_features(fire_scenario_data)
        if features is None:
            return jsonify({"error": "Error preparing fire scenario features"}), 500

        model = model_cache["model"]
        prediction = model.predict(features)[0]

        prediction_proba = None
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(features)[0]
            prediction_proba = {"no_fire": float(proba[0]), "fire": float(proba[1])}

        prediction_result = "fire" if prediction == 1 else "no_fire"
        PREDICTION_COUNT.labels(
            prediction_type="fire_scenario", result=prediction_result
        ).inc()

        result = {
            "input_data": fire_scenario_data,
            "scenario": "fire_conditions",
            "prediction": {
                "prediction": int(prediction),
                "prediction_label": prediction_result,
                "confidence": prediction_proba,
                "timestamp": datetime.now().isoformat(),
            },
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Fire scenario prediction error: {e}")
        ERROR_COUNT.labels(error_type="fire_scenario_error").inc()
        return jsonify({"error": str(e)}), 500


# New API Endpoints


@app.route("/sensors/schema", methods=["GET"])
@track_metrics
def get_sensor_schema():
    """Get sensor data schema and validation rules."""
    try:
        return jsonify(SENSOR_SCHEMA)
    except Exception as e:
        logger.error(f"Schema endpoint error: {e}")
        ERROR_COUNT.labels(error_type="schema_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/model/reload", methods=["POST"])
@track_metrics
def reload_model():
    """Force reload of the ML model."""
    try:
        success = load_model_from_pickle()

        if success:
            return jsonify(
                {
                    "status": "success",
                    "message": "Model reloaded successfully",
                    "model_info": model_cache["model_info"],
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            ERROR_COUNT.labels(error_type="model_reload_failed").inc()
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Failed to reload model",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Model reload error: {e}")
        ERROR_COUNT.labels(error_type="model_reload_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/predictions/stats", methods=["GET"])
@track_metrics
def get_prediction_stats():
    """Get prediction statistics."""
    try:
        # Calculate additional stats
        total = prediction_stats["total_predictions"]
        fire_rate = (
            (prediction_stats["fire_predictions"] / total * 100) if total > 0 else 0
        )
        no_fire_rate = (
            (prediction_stats["no_fire_predictions"] / total * 100) if total > 0 else 0
        )

        stats = {
            **prediction_stats,
            "fire_detection_rate_percent": round(fire_rate, 2),
            "safe_detection_rate_percent": round(no_fire_rate, 2),
            "uptime_seconds": time.time() - prediction_stats["last_reset"],
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Stats endpoint error: {e}")
        ERROR_COUNT.labels(error_type="stats_error").inc()
        return jsonify({"error": str(e)}), 500


@app.route("/config", methods=["GET"])
@track_metrics
def get_api_config():
    """Get API configuration information."""
    try:
        config_info = {
            **API_CONFIG,
            "model_path": MODEL_PATH,
            "model_loaded": model_cache["model"] is not None,
            "endpoints": [
                {
                    "path": "/predict",
                    "method": "POST",
                    "description": "Single prediction",
                },
                {
                    "path": "/predict/batch",
                    "method": "POST",
                    "description": "Batch predictions",
                },
                {
                    "path": "/predict/sample",
                    "method": "GET",
                    "description": "Test sample data",
                },
                {
                    "path": "/predict/fire-scenario",
                    "method": "GET",
                    "description": "Fire scenario test",
                },
                {
                    "path": "/model/info",
                    "method": "GET",
                    "description": "Model information",
                },
                {
                    "path": "/model/reload",
                    "method": "POST",
                    "description": "Reload model",
                },
                {"path": "/health", "method": "GET", "description": "Health check"},
                {
                    "path": "/validate",
                    "method": "POST",
                    "description": "Data validation",
                },
                {
                    "path": "/sensors/schema",
                    "method": "GET",
                    "description": "Sensor schema",
                },
                {
                    "path": "/predictions/stats",
                    "method": "GET",
                    "description": "Prediction statistics",
                },
                {
                    "path": "/config",
                    "method": "GET",
                    "description": "API configuration",
                },
                {
                    "path": "/metrics",
                    "method": "GET",
                    "description": "Prometheus metrics",
                },
            ],
            "timestamp": datetime.now().isoformat(),
        }

        return jsonify(config_info)

    except Exception as e:
        logger.error(f"Config endpoint error: {e}")
        ERROR_COUNT.labels(error_type="config_error").inc()
        return jsonify({"error": str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


# Application initialization
def create_app():
    """Create and configure Flask app."""
    app.start_time = time.time()

    # Try to load model on startup
    if not load_model_from_pickle():
        logger.warning(
            "⚠️ Could not load model on startup - API will have limited functionality"
        )

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IoT Smoke Detection API")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--model-path", type=str, help="Path to model pickle file")

    args = parser.parse_args()

    # Override model path if provided
    if args.model_path:
        global MODEL_PATH
        MODEL_PATH = args.model_path

    # Create app
    app = create_app()

    # Run app
    logger.info(f"🚀 Starting IoT Smoke Detection API on {args.host}:{args.port}")
    logger.info(f"📁 Model path: {MODEL_PATH}")
    app.run(host=args.host, port=args.port, debug=args.debug)
