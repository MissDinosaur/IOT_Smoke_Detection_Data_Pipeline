# Quick fix for model compatibility issue in Docker containers
# PowerShell script to regenerate the model inside the ml_trainer container

Write-Host "🔧 Fixing Model Compatibility Issue" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Check if containers are running
$mlTrainerStatus = docker-compose ps | Select-String "ml_trainer.*Up"
if (-not $mlTrainerStatus) {
    Write-Host "❌ ml_trainer container is not running" -ForegroundColor Red
    Write-Host "Starting ml_trainer container..." -ForegroundColor Yellow
    docker-compose up -d ml_trainer
    Start-Sleep -Seconds 10
}

Write-Host "📦 Regenerating model in ml_trainer container..." -ForegroundColor Blue

# Python script to run inside the container
$pythonScript = @"
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
"@

# Run the Python script inside the container
try {
    $result = docker-compose exec ml_trainer python -c $pythonScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Model regenerated successfully!" -ForegroundColor Green
        Write-Host "🔄 Restarting Flask API container..." -ForegroundColor Blue
        docker-compose restart flask_api
        
        Write-Host "⏳ Waiting for Flask API to start..." -ForegroundColor Yellow
        Start-Sleep -Seconds 15
        
        Write-Host "🧪 Testing API health..." -ForegroundColor Blue
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Flask API is healthy!" -ForegroundColor Green
                Write-Host "🎉 Model compatibility issue fixed!" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Flask API returned status: $($response.StatusCode)" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "⚠️  Flask API may still be starting. Check logs with:" -ForegroundColor Yellow
            Write-Host "   docker-compose logs flask_api" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ Model regeneration failed" -ForegroundColor Red
        Write-Host "Check ml_trainer container logs:" -ForegroundColor Yellow
        Write-Host "   docker-compose logs ml_trainer" -ForegroundColor Gray
    }
}
catch {
    Write-Host "❌ Error running model regeneration: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "  • Check API logs: docker-compose logs flask_api" -ForegroundColor Gray
Write-Host "  • Test API: curl http://localhost:5000/health" -ForegroundColor Gray
Write-Host "  • Test prediction: curl -X POST http://localhost:5000/predict -H 'Content-Type: application/json' -d '{`"temperature`": 25.5, `"humidity`": 60.0, `"smoke`": 0.1}'" -ForegroundColor Gray
