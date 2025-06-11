#!/bin/bash

# Startup script for Spark Streaming Processor
# Production-ready script with health checks and monitoring

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SPARK_APP_PATH="$PROJECT_ROOT/data_processing/stream_processing/spark_streaming_processor.py"
LOG_DIR="/app/logs"
PID_FILE="/app/spark_streaming.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

# Check if Spark streaming is already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Wait for Kafka to be available
wait_for_kafka() {
    local kafka_host="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"
    local max_attempts=30
    local attempt=1
    
    log "Waiting for Kafka at $kafka_host..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z ${kafka_host%:*} ${kafka_host#*:} 2>/dev/null; then
            log_success "Kafka is available"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts: Kafka not ready, waiting 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Kafka is not available after $max_attempts attempts"
    return 1
}

# Check system resources
check_resources() {
    log "Checking system resources..."
    
    # Check memory
    local available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    local required_memory=2048  # 2GB minimum
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        log_warning "Low memory: ${available_memory}MB available, ${required_memory}MB recommended"
    else
        log "Memory check passed: ${available_memory}MB available"
    fi
    
    # Check disk space
    local available_disk=$(df /app | awk 'NR==2 {print $4}')
    local required_disk=1048576  # 1GB minimum in KB
    
    if [ "$available_disk" -lt "$required_disk" ]; then
        log_warning "Low disk space: $(($available_disk/1024))MB available"
    else
        log "Disk space check passed: $(($available_disk/1024))MB available"
    fi
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    mkdir -p "$LOG_DIR"
    mkdir -p "/app/data/checkpoints"
    mkdir -p "/app/data/processed_stream"
    mkdir -p "/app/logs/spark-events"
    
    # Set permissions
    chmod 755 "$LOG_DIR"
    chmod 755 "/app/data/checkpoints"
    chmod 755 "/app/data/processed_stream"
    
    log "Directories setup completed"
}

# Start Spark streaming
start_streaming() {
    log "Starting Spark streaming processor..."
    
    # Check if already running
    if check_running; then
        log_warning "Spark streaming is already running (PID: $(cat $PID_FILE))"
        return 0
    fi
    
    # Setup environment
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export SPARK_HOME="${SPARK_HOME:-/opt/spark}"
    export PYSPARK_PYTHON="${PYSPARK_PYTHON:-python3}"
    
    # Parse command line arguments
    local args=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --kafka-servers)
                args="$args --kafka-servers $2"
                shift 2
                ;;
            --kafka-topic)
                args="$args --kafka-topic $2"
                shift 2
                ;;
            --window-duration)
                args="$args --window-duration $2"
                shift 2
                ;;
            --slide-duration)
                args="$args --slide-duration $2"
                shift 2
                ;;
            --enable-console)
                args="$args --enable-console"
                shift
                ;;
            --disable-file-output)
                args="$args --disable-file-output"
                shift
                ;;
            *)
                log_warning "Unknown argument: $1"
                shift
                ;;
        esac
    done
    
    # Start the application
    log "Executing: python3 $SPARK_APP_PATH $args"
    
    nohup python3 "$SPARK_APP_PATH" $args \
        > "$LOG_DIR/spark_streaming.log" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 5
    if ps -p "$pid" > /dev/null 2>&1; then
        log_success "Spark streaming started successfully (PID: $pid)"
        log "Logs available at: $LOG_DIR/spark_streaming.log"
        log "Spark UI available at: http://localhost:4040"
        return 0
    else
        log_error "Failed to start Spark streaming"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Stop Spark streaming
stop_streaming() {
    log "Stopping Spark streaming processor..."
    
    if ! check_running; then
        log_warning "Spark streaming is not running"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    
    # Send SIGTERM for graceful shutdown
    log "Sending SIGTERM to process $pid..."
    kill -TERM "$pid" 2>/dev/null || true
    
    # Wait for graceful shutdown
    local timeout=30
    local count=0
    while [ $count -lt $timeout ] && ps -p "$pid" > /dev/null 2>&1; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        log_warning "Graceful shutdown timeout, force killing..."
        kill -KILL "$pid" 2>/dev/null || true
        sleep 2
    fi
    
    # Clean up
    rm -f "$PID_FILE"
    log_success "Spark streaming stopped"
}

# Show status
show_status() {
    if check_running; then
        local pid=$(cat "$PID_FILE")
        log_success "Spark streaming is running (PID: $pid)"
        
        # Show resource usage
        local cpu_usage=$(ps -p "$pid" -o %cpu --no-headers 2>/dev/null || echo "N/A")
        local mem_usage=$(ps -p "$pid" -o %mem --no-headers 2>/dev/null || echo "N/A")
        
        echo "  CPU Usage: ${cpu_usage}%"
        echo "  Memory Usage: ${mem_usage}%"
        echo "  Log file: $LOG_DIR/spark_streaming.log"
        echo "  Spark UI: http://localhost:4040"
    else
        log "Spark streaming is not running"
    fi
}

# Show logs
show_logs() {
    local lines="${1:-50}"
    
    if [ -f "$LOG_DIR/spark_streaming.log" ]; then
        log "Showing last $lines lines of Spark streaming logs:"
        echo "----------------------------------------"
        tail -n "$lines" "$LOG_DIR/spark_streaming.log"
    else
        log_warning "Log file not found: $LOG_DIR/spark_streaming.log"
    fi
}

# Main function
main() {
    case "${1:-start}" in
        start)
            setup_directories
            check_resources
            wait_for_kafka
            shift
            start_streaming "$@"
            ;;
        stop)
            stop_streaming
            ;;
        restart)
            stop_streaming
            sleep 2
            setup_directories
            check_resources
            wait_for_kafka
            shift
            start_streaming "$@"
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-50}"
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|logs} [options]"
            echo ""
            echo "Commands:"
            echo "  start     Start Spark streaming processor"
            echo "  stop      Stop Spark streaming processor"
            echo "  restart   Restart Spark streaming processor"
            echo "  status    Show current status"
            echo "  logs      Show recent logs (default: 50 lines)"
            echo ""
            echo "Start options:"
            echo "  --kafka-servers <servers>    Kafka bootstrap servers"
            echo "  --kafka-topic <topic>        Kafka topic to consume"
            echo "  --window-duration <duration> Window duration (e.g., '5 minutes')"
            echo "  --slide-duration <duration>  Slide duration (e.g., '1 minute')"
            echo "  --enable-console             Enable console output"
            echo "  --disable-file-output        Disable file output"
            echo ""
            echo "Examples:"
            echo "  $0 start --kafka-servers localhost:9092 --enable-console"
            echo "  $0 logs 100"
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"
