#!/bin/bash
"""
IoT Smoke Detection System Test Script

This script tests the system after startup to ensure all components are working correctly.
"""

set -e

echo "🧪 IoT Smoke Detection System - Testing"
echo "=" * 50

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Test Flask API Health
print_status "Testing Flask API health..."
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    print_success "Flask API is healthy"
else
    print_error "Flask API health check failed"
fi

# Test Model Info
print_status "Testing model info endpoint..."
if curl -s http://localhost:5000/model/info | grep -q "model_name"; then
    print_success "Model info endpoint working"
else
    print_error "Model info endpoint failed"
fi

# Test Prediction
print_status "Testing prediction endpoint..."
prediction_response=$(curl -s -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
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
    "NC2.5": 20.0
  }')

if echo "$prediction_response" | grep -q "prediction"; then
    print_success "Prediction endpoint working"
    echo "  Response: $prediction_response"
else
    print_error "Prediction endpoint failed"
fi

# Test Model File
print_status "Checking model file..."
if [ -f "./models/smoke_detection_model.pkl" ]; then
    file_size=$(stat -f%z "./models/smoke_detection_model.pkl" 2>/dev/null || stat -c%s "./models/smoke_detection_model.pkl" 2>/dev/null)
    print_success "Model file exists (${file_size} bytes)"
else
    print_error "Model file not found locally"
fi

# Test Services Status
print_status "Checking Docker services..."
docker-compose ps

echo ""
print_success "🎉 System testing completed!"
print_status "Run the full test suite with: python tests/run_streaming_tests.py --all"
