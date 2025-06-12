#!/bin/bash
"""
IoT Smoke Detection System Startup Script

This script orchestrates the startup of the entire IoT smoke detection pipeline
with proper dependency management and model training coordination.

Features:
1. Sets up models directory structure
2. Starts ML training first and waits for completion
3. Starts dependent services only after models are ready
4. Provides status monitoring and health checks
"""

set -e  # Exit on any error

echo "🔥 IoT Smoke Detection Data Pipeline - System Startup"
echo "=" * 60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local max_attempts=${2:-30}
    local attempt=1
    
    print_status "Checking health of $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service_name | grep -q "healthy\|Up"; then
            print_success "$service_name is healthy"
            return 0
        fi
        
        print_status "Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 10
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to become healthy"
    return 1
}

# Function to wait for model file
wait_for_model() {
    local model_path="./models/smoke_detection_model.pkl"
    local max_wait_minutes=${1:-60}
    local max_attempts=$((max_wait_minutes * 2))  # Check every 30 seconds
    local attempt=1
    
    print_status "Waiting for ML model to be trained and saved..."
    print_status "Model path: $model_path"
    print_status "Maximum wait time: $max_wait_minutes minutes"
    
    while [ $attempt -le $max_attempts ]; do
        if [ -f "$model_path" ]; then
            local file_size=$(stat -f%z "$model_path" 2>/dev/null || stat -c%s "$model_path" 2>/dev/null || echo "0")
            if [ "$file_size" -gt 1000 ]; then  # At least 1KB
                print_success "Model file found and appears valid (${file_size} bytes)"
                return 0
            else
                print_warning "Model file exists but appears too small (${file_size} bytes)"
            fi
        fi
        
        local elapsed_minutes=$((attempt / 2))
        print_status "Waiting for model... (${elapsed_minutes}/${max_wait_minutes} minutes)"
        sleep 30
        attempt=$((attempt + 1))
    done
    
    print_error "Model file not found after $max_wait_minutes minutes"
    return 1
}

# Step 1: Setup models directory
print_status "Setting up models directory structure..."
if [ -f "scripts/setup_models_directory.sh" ]; then
    chmod +x scripts/setup_models_directory.sh
    ./scripts/setup_models_directory.sh
else
    print_warning "Setup script not found, creating models directory manually..."
    mkdir -p ./models
    chmod 755 ./models
fi

# Step 2: Check Docker Compose file
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found!"
    exit 1
fi

print_success "Docker Compose configuration found"

# Step 3: Start infrastructure services first
print_status "Starting infrastructure services (Kafka, Zookeeper, Postgres)..."
docker-compose up -d kafka zookeeper postgres

print_status "Waiting for infrastructure services to be ready..."
sleep 30

# Step 4: Start ML training service
print_status "Starting ML training service..."
docker-compose up -d ml_trainer

print_status "ML training started. This may take 30-60 minutes for initial model training..."
print_status "You can monitor progress with: docker-compose logs -f ml_trainer"

# Step 5: Wait for model to be trained and available
if ! wait_for_model 60; then
    print_error "Failed to wait for model training completion"
    print_status "You can:"
    print_status "1. Check ML training logs: docker-compose logs ml_trainer"
    print_status "2. Continue startup anyway: docker-compose up -d"
    print_status "3. Restart this script: ./start_system.sh"
    exit 1
fi

# Step 6: Start Flask API (depends on ML model)
print_status "Starting Flask API service..."
docker-compose up -d flask_api

print_status "Waiting for Flask API to be ready..."
if ! check_service_health flask_api 20; then
    print_warning "Flask API health check failed, but continuing..."
fi

# Step 7: Start remaining services
print_status "Starting remaining services..."
docker-compose up -d

# Step 8: Final health checks
print_status "Performing final health checks..."

services=("kafka" "flask_api" "ml_trainer")
for service in "${services[@]}"; do
    if ! check_service_health $service 10; then
        print_warning "Service $service may not be fully ready"
    fi
done

# Step 9: Display system status
print_success "System startup completed!"
echo ""
print_status "System Status:"
docker-compose ps

echo ""
print_status "Service URLs:"
echo "  🌐 Flask API:        http://localhost:5000"
echo "  📊 Grafana:          http://localhost:3000 (admin/admin)"
echo "  📈 Prometheus:       http://localhost:9090"
echo "  ⚡ Spark UI:         http://localhost:4040"
echo "  🔄 Airflow:          http://localhost:8080 (admin/admin)"

echo ""
print_status "Useful Commands:"
echo "  📋 View all logs:    docker-compose logs -f"
echo "  🤖 ML training logs: docker-compose logs -f ml_trainer"
echo "  🌐 API logs:         docker-compose logs -f flask_api"
echo "  🛑 Stop system:      docker-compose down"
echo "  🔄 Restart system:   docker-compose restart"

echo ""
print_status "Model Information:"
if [ -f "./models/smoke_detection_model.pkl" ]; then
    local model_size=$(stat -f%z "./models/smoke_detection_model.pkl" 2>/dev/null || stat -c%s "./models/smoke_detection_model.pkl" 2>/dev/null || echo "unknown")
    print_success "Model file: ./models/smoke_detection_model.pkl (${model_size} bytes)"
    print_status "Model will be retrained daily at 2 AM"
else
    print_warning "Model file not found locally (may be in Docker volume)"
fi

echo ""
print_success "🎉 IoT Smoke Detection System is ready!"
print_status "The system will automatically retrain the ML model daily at 2 AM"
print_status "Monitor the system with: docker-compose logs -f"
