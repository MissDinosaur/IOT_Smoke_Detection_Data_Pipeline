# Models Directory

This directory contains trained ML models for the IoT Smoke Detection system.

## Files:
- `smoke_detection_model.pkl` - Current production model used by Flask API
- `model_backup_*.pkl` - Backup models with timestamps

## Model Updates:
- Models are automatically retrained daily at 2 AM
- New models replace the existing `smoke_detection_model.pkl`
- Previous models are backed up with timestamps

## Usage:
- Flask API loads models from this directory
- Models are shared between Docker containers via volume mounts
- Local copies are saved here for persistence across container restarts

## Model Format:
Models are saved as pickle files containing:
- Trained scikit-learn model
- Feature column names
- Model metadata and metrics
- Preprocessing scaler (if used)
