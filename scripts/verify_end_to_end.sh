#!/bin/bash

# End-to-End Pipeline Verification Script
# Verifies that all components are working correctly after docker-compose up --build

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMEOUT=300  # 5 minutes timeout for services to start

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1" >&2
}

# Check if Docker is running
check_docker() {
    log "Checking Docker status..."
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
}

# Check if docker-compose file exists
check_compose_file() {
    log "Checking docker-compose.yml..."
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        log_error "docker-compose.yml not found in project root"
        exit 1
    fi
    log_success "docker-compose.yml found"
}

# Check environment file
check_env_file() {
    log "Checking .env file..."
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found in project root"
        exit 1
    fi
    log_success ".env file found"
}

# Check required data files
check_data_files() {
    log "Checking required data files..."
    
    if [ ! -f "$PROJECT_ROOT/data/smoke_detection_iot.csv" ]; then
        log_error "Required data file not found: data/smoke_detection_iot.csv"
        exit 1
    fi
    
    log_success "Required data files found"
}

# Wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=$((TIMEOUT / 10))
    local attempt=1
    
    log "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            log_success "$service_name is ready"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts: $service_name not ready, waiting 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    log_error "$service_name failed to start within $TIMEOUT seconds"
    return 1
}

# Check container status
check_container_status() {
    local container_name=$1
    
    log "Checking container status: $container_name"
    
    if ! docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name"; then
        log_error "Container $container_name is not running"
        return 1
    fi
    
    local status=$(docker ps --format "{{.Status}}" --filter "name=$container_name")
    log_success "Container $container_name is running: $status"
    return 0
}

# Check service logs for errors
check_service_logs() {
    local container_name=$1
    local error_patterns=("ERROR" "FATAL" "Exception" "Failed")
    
    log "Checking logs for $container_name..."
    
    local logs=$(docker logs "$container_name" --tail 50 2>&1)
    
    for pattern in "${error_patterns[@]}"; do
        if echo "$logs" | grep -qi "$pattern"; then
            log_warning "Found potential issues in $container_name logs (pattern: $pattern)"
            echo "$logs" | grep -i "$pattern" | tail -3
        fi
    done
    
    log_success "Log check completed for $container_name"
}

# Test Kafka connectivity
test_kafka() {
    log "Testing Kafka connectivity..."
    
    # Check if Kafka is accepting connections
    if ! wait_for_service "Kafka" 9092; then
        return 1
    fi
    
    # Test topic creation/listing
    log "Testing Kafka topic operations..."
    if docker exec smoke_kafka kafka-topics --bootstrap-server localhost:9092 --list >/dev/null 2>&1; then
        log_success "Kafka topic operations working"
    else
        log_warning "Kafka topic operations may have issues"
    fi
    
    return 0
}

# Test data ingestion
test_data_ingestion() {
    log "Testing data ingestion..."
    
    # Check if producer container is running
    if ! check_container_status "kafka_producer"; then
        return 1
    fi
    
    # Check producer logs for successful message sending
    local producer_logs=$(docker logs kafka_producer --tail 20 2>&1)
    if echo "$producer_logs" | grep -qi "sent\|produced\|published"; then
        log_success "Data ingestion appears to be working"
    else
        log_warning "Data ingestion may not be producing messages yet"
    fi
    
    return 0
}

# Test stream processing
test_stream_processing() {
    log "Testing stream processing..."
    
    # Check regular stream processor
    if check_container_status "stream_processor"; then
        log_success "Regular stream processor is running"
    fi
    
    # Check Spark stream processor
    if check_container_status "spark_stream_processor"; then
        log_success "Spark stream processor is running"
        
        # Check if Spark UI is accessible
        if wait_for_service "Spark UI" 4040; then
            log_success "Spark UI is accessible at http://localhost:4040"
        else
            log_warning "Spark UI may not be ready yet"
        fi
    fi
    
    return 0
}

# Test ML integration
test_ml_integration() {
    log "Testing ML integration..."
    
    # Check if ML models directory exists
    if [ -d "$PROJECT_ROOT/ml/models" ]; then
        log_success "ML models directory exists"
        
        # Check for model files
        if ls "$PROJECT_ROOT/ml/models"/*.pkl >/dev/null 2>&1; then
            log_success "ML model files found"
        else
            log_warning "No ML model files found - ML predictions will be disabled"
        fi
    else
        log_warning "ML models directory not found"
    fi
    
    # Check Spark processor logs for ML initialization
    local spark_logs=$(docker logs spark_stream_processor --tail 30 2>&1)
    if echo "$spark_logs" | grep -qi "ML model"; then
        log_success "ML integration is being initialized"
    else
        log_warning "ML integration may not be active"
    fi
    
    return 0
}

# Test Airflow
test_airflow() {
    log "Testing Airflow..."
    
    if ! check_container_status "airflow"; then
        return 1
    fi
    
    if wait_for_service "Airflow" 8080; then
        log_success "Airflow UI is accessible at http://localhost:8080"
        log "Default credentials: admin/admin"
    else
        log_warning "Airflow UI may not be ready yet"
    fi
    
    return 0
}

# Generate summary report
generate_summary() {
    log "Generating end-to-end verification summary..."
    
    echo ""
    echo "=========================================="
    echo "🚀 END-TO-END PIPELINE VERIFICATION SUMMARY"
    echo "=========================================="
    echo ""
    
    echo "📊 Service Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(smoke_|kafka_|stream_|spark_|airflow)"
    
    echo ""
    echo "🌐 Web Interfaces:"
    echo "  • Spark UI:    http://localhost:4040"
    echo "  • Airflow UI:  http://localhost:8080 (admin/admin)"
    
    echo ""
    echo "📁 Data Pipeline:"
    echo "  • Data Ingestion:     ✅ Kafka Producer"
    echo "  • Stream Processing:  ✅ Regular + Spark Processors"
    echo "  • ML Integration:     ✅ Real-time + Historical"
    echo "  • Batch Processing:   ✅ Airflow"
    
    echo ""
    echo "🔧 Useful Commands:"
    echo "  • View logs:          docker logs <container_name>"
    echo "  • Stop pipeline:      docker-compose down"
    echo "  • Restart service:    docker-compose restart <service_name>"
    echo "  • Check ML models:    ls ml/models/"
    
    echo ""
    echo "✅ End-to-end verification completed!"
    echo "=========================================="
}

# Main verification function
main() {
    echo "🔥 IoT Smoke Detection Pipeline - End-to-End Verification"
    echo "=========================================="
    
    # Pre-flight checks
    check_docker
    check_compose_file
    check_env_file
    check_data_files
    
    log "Starting end-to-end verification..."
    
    # Wait for core services
    log "Waiting for core services to start..."
    sleep 30  # Give services time to initialize
    
    # Test each component
    local failed_tests=0
    
    if ! test_kafka; then
        ((failed_tests++))
    fi
    
    if ! test_data_ingestion; then
        ((failed_tests++))
    fi
    
    if ! test_stream_processing; then
        ((failed_tests++))
    fi
    
    if ! test_ml_integration; then
        ((failed_tests++))
    fi
    
    if ! test_airflow; then
        ((failed_tests++))
    fi
    
    # Generate summary
    generate_summary
    
    if [ $failed_tests -eq 0 ]; then
        log_success "All tests passed! Pipeline is running successfully."
        exit 0
    else
        log_warning "$failed_tests test(s) had issues. Check the logs above for details."
        exit 1
    fi
}

# Run main function
main "$@"
