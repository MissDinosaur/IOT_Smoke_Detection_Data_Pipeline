#!/bin/bash
"""
Setup script to create models directory structure for ML training.

This script ensures that the local models directory exists and has proper permissions
for saving trained models that can be accessed by other containers and the host system.
"""

echo "🔧 Setting up models directory structure..."

# Create models directory in project root if it doesn't exist
MODELS_DIR="./models"
if [ ! -d "$MODELS_DIR" ]; then
    mkdir -p "$MODELS_DIR"
    echo "✅ Created models directory: $MODELS_DIR"
else
    echo "✅ Models directory already exists: $MODELS_DIR"
fi

# Set proper permissions
chmod 755 "$MODELS_DIR"
echo "✅ Set permissions for models directory"

# Create a README file explaining the directory
cat > "$MODELS_DIR/README.md" << 'EOF'
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
EOF

echo "✅ Created README.md in models directory"

# Create .gitkeep to ensure directory is tracked by git
touch "$MODELS_DIR/.gitkeep"
echo "✅ Created .gitkeep file"

# Create .gitignore to ignore large model files but keep structure
cat > "$MODELS_DIR/.gitignore" << 'EOF'
# Ignore large model files
*.pkl

# Keep directory structure
!.gitkeep
!README.md
EOF

echo "✅ Created .gitignore for models directory"

echo "🎉 Models directory setup completed successfully!"
echo ""
echo "📁 Directory structure:"
ls -la "$MODELS_DIR"
echo ""
echo "💡 The models directory is now ready for ML training."
echo "   Trained models will be saved here and shared with Docker containers."
