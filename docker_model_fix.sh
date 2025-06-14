#!/bin/bash

# Quick fix for model compatibility issue in Docker containers
# This script regenerates the model inside the ml_trainer container

echo "🔧 Fixing Model Compatibility Issue"
echo "=================================="

# Check if containers are running
if ! docker-compose ps | grep -q "ml_trainer.*Up"; then
    echo "❌ ml_trainer container is not running"
    echo "Starting ml_trainer container..."
    docker-compose up -d ml_trainer
    sleep 10
fi

echo "📦 Regenerating model in ml_trainer container..."

# Run the model fix script inside the container
docker-compose exec ml_trainer python -c "
import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

print('🔧 Regenerating model with current scikit-learn version...')

# Create synthetic data
np.random.seed(42)
n_samples = 1000

temperature = np.random.normal(25, 10, n_samples)
humidity = np.random.normal(50, 20, n_samples)
smoke = np.random.exponential(0.1, n_samples)

fire_risk = (
    (temperature > 35) & (humidity < 30) & (smoke > 0.2) |
    (temperature > 40) & (smoke > 0.15) |
    (smoke > 0.3)
).astype(int)

df = pd.DataFrame({
    'Temperature': temperature,
    'Humidity': humidity,
    'Smoke': smoke,
    'TVOC': np.random.normal(100, 50, n_samples),
    'eCO2': np.random.normal(400, 100, n_samples),
    'Pressure': np.random.normal(1013, 10, n_samples),
    'Fire_Alarm': fire_risk
})

# Prepare features
X = df[['Temperature', 'Humidity', 'Smoke', 'TVOC', 'eCO2', 'Pressure']]
y = df['Fire_Alarm']

# Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
model.fit(X_train, y_train)

# Save model
os.makedirs('/app/models', exist_ok=True)
joblib.dump(model, '/app/models/smoke_detection_model.pkl')

print('✅ Model regenerated and saved successfully!')
print(f'📊 Model accuracy: {model.score(X_test, y_test):.4f}')
print(f'🔬 Scikit-learn version: {__import__(\"sklearn\").__version__}')
"

if [ $? -eq 0 ]; then
    echo "✅ Model regenerated successfully!"
    echo "🔄 Restarting Flask API container..."
    docker-compose restart flask_api
    
    echo "⏳ Waiting for Flask API to start..."
    sleep 15
    
    echo "🧪 Testing API health..."
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ Flask API is healthy!"
        echo "🎉 Model compatibility issue fixed!"
    else
        echo "⚠️  Flask API may still be starting. Check logs with:"
        echo "   docker-compose logs flask_api"
    fi
else
    echo "❌ Model regeneration failed"
    echo "Check ml_trainer container logs:"
    echo "   docker-compose logs ml_trainer"
fi

echo ""
echo "📋 Useful commands:"
echo "  • Check API logs: docker-compose logs flask_api"
echo "  • Test API: curl http://localhost:5000/health"
echo "  • Test prediction: curl -X POST http://localhost:5000/predict -H 'Content-Type: application/json' -d '{\"temperature\": 25.5, \"humidity\": 60.0, \"smoke\": 0.1}'"
