# ML Models Directory

This directory contains trained machine learning models for the IoT smoke detection system.

## Model Files

Place your trained models here with the following naming convention:
- `best_model.pkl` - The primary trained model (default)
- `model_v1.pkl` - Version 1 of the model
- `model_v2.pkl` - Version 2 of the model

## Model Format

Models should be saved using the format expected by the `SmokeDetectionModelLoader`:

```python
model_data = {
    "model": trained_sklearn_model,
    "scaler": fitted_scaler,  # Optional
    "feature_columns": list_of_feature_names,
    "metadata": {
        "model_type": "RandomForestClassifier",
        "training_date": "2024-01-01",
        "version": "1.0",
        "accuracy": 0.95
    }
}

with open("best_model.pkl", "wb") as f:
    pickle.dump(model_data, f)
```

## Training Models

To train and save models, use the ML training pipeline:

```bash
# Train models using the training pipeline
python ml/training/train_model.py --data data/smoke_detection_iot.csv

# The trained model will be automatically saved to this directory
```

## Using Models in Streaming

The Spark streaming processor will automatically load models from this directory:

```bash
# Use default model (best_model.pkl)
python data_processing/stream_processing/spark_streaming_processor.py

# Use specific model
python data_processing/stream_processing/spark_streaming_processor.py \
    --ml-model-path ml/models/model_v2.pkl
```

## Model Fallback

If no model is found, the streaming processor will:
1. Log a warning about missing ML model
2. Continue processing with statistical analytics only
3. Disable ML predictions gracefully

This ensures the pipeline continues to work even without trained models.
