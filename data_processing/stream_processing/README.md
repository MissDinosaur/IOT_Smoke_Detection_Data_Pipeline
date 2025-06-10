# Stream Processing Module

This module handles real-time processing of IoT smoke detection data using Kafka and Spark Streaming with advanced analytics and anomaly detection capabilities.

## Components

### Core Processing Components

- **`transform_and_save_stream.py`**: Enhanced Kafka consumer with validation, error handling, and basic anomaly detection
- **`spark_streaming_processor.py`**: Spark Streaming implementation for scalable windowed analytics
- **`detect_anomalies.py`**: Advanced anomaly detection with multiple algorithms
- **`error_handler.py`**: Robust error handling and validation utilities

### Key Features

- **Real-time Data Validation**: Validates incoming sensor data structure and ranges
- **Multi-level Anomaly Detection**: Threshold-based, statistical, and pattern-based detection
- **Windowed Analytics**: 5-minute sliding windows with 1-minute updates
- **Error Handling**: Automatic retry mechanisms and graceful error recovery
- **Comprehensive Logging**: Structured logging for monitoring and debugging

## How to Start the Streaming Pipeline

### Prerequisites

1. Ensure Kafka and Zookeeper are running:
   ```bash
   docker-compose up -d zookeeper kafka
   ```

2. Verify Kafka topic creation:
   ```bash
   docker exec -it smoke_kafka kafka-topics --list --bootstrap-server localhost:9092
   ```

### Starting Components

#### Option 1: Basic Kafka Consumer (Lightweight)
```bash
# Start the Kafka producer
docker-compose up -d smoke_kafka_producer

# Run the enhanced Kafka consumer
python data_processing/stream_processing/transform_and_save_stream.py
```

#### Option 2: Spark Streaming (Scalable Analytics)
```bash
# Start the Kafka producer
docker-compose up -d smoke_kafka_producer

# Run Spark streaming processor
python data_processing/stream_processing/spark_streaming_processor.py
```

#### Option 3: Docker Compose (Recommended)
Add to your `docker-compose.yml`:
```yaml
stream_processor:
  build:
    context: .
    dockerfile: data_processing/stream_processing/Dockerfile
  container_name: stream_processor
  depends_on:
    - kafka
  environment:
    KAFKA_BOOTSTRAP_SERVERS: kafka:9092
  volumes:
    - ./data:/app/data
    - ./data_processing/stream_processing:/app/stream_processing
  command: python stream_processing/spark_streaming_processor.py
```

## Analytics and Alerts

### Real-time Analytics (Spark Streaming)

**Window Configuration:**
- Window Duration: 5 minutes
- Slide Duration: 1 minute
- Watermark: 10 minutes for late data handling

**Computed Metrics:**
- Average temperature, humidity, TVOC, eCO2, PM2.5, pressure
- Maximum and minimum temperature
- Temperature standard deviation
- Record count per window
- Fire alarm count

### Alert Thresholds

#### Temperature Alerts
- **Critical Low**: < -20°C
- **Low**: < 0°C
- **Medium High**: > 40°C
- **High**: > 50°C
- **Critical High**: > 70°C

#### Air Quality Alerts
- **TVOC**: Medium > 500 ppb, High > 1000 ppb, Critical > 2000 ppb
- **eCO2**: Medium > 800 ppm, High > 1000 ppm, Critical > 1500 ppm
- **PM2.5**: Medium > 25 μg/m³, High > 35 μg/m³, Critical > 50 μg/m³

#### Humidity Alerts
- **Critical Low**: < 5%
- **Low**: < 15%
- **Medium High**: > 80%
- **High**: > 90%
- **Critical High**: > 95%

#### Fire Pattern Detection
- **Indicators**: High temperature (>45°C), High TVOC (>800 ppb), High eCO2 (>800 ppm), High PM2.5 (>30 μg/m³)
- **High Risk**: 2+ indicators active
- **Critical**: 3+ indicators active or fire alarm triggered

### Statistical Anomaly Detection
- **Z-Score Threshold**: 3.0 (configurable)
- **Rolling Window**: 100 data points
- **Minimum Data**: 30 points for statistical analysis
- **Severity**: Medium (Z > 3.0), High (Z > 4.0)

## Output Locations

### Logs
- **Stream Processing**: `stream_processing.log`
- **Spark Streaming**: `spark_streaming.log`
- **Console Output**: Real-time alerts and metrics

### Data Storage
- **Raw Processed Data**: `/app/data/processed_stream/` (CSV format)
- **Historical Data**: `/app/data/historical_smoke_data.csv`
- **Checkpoints**: `/app/data/checkpoints/` (Spark streaming state)

### Monitoring Endpoints
- **Spark UI**: http://localhost:4040 (when Spark is running)
- **Kafka Manager**: Available through Docker logs
- **Application Logs**: `docker-compose logs -f stream_processor`

## Error Handling

### Kafka Connection Issues
- **Automatic Retry**: 5 attempts with 10-second delays
- **Exponential Backoff**: Configurable delay between retries
- **Graceful Degradation**: Continues processing after connection recovery

### Data Validation
- **Schema Validation**: Checks for required fields and data types
- **Range Validation**: Validates sensor readings within expected ranges
- **Missing Data Handling**: Uses default values or skips invalid records
- **Logging**: All validation errors are logged with details

### Processing Errors
- **Exception Handling**: Comprehensive try-catch blocks
- **Error Isolation**: Single message failures don't stop the stream
- **Recovery Mechanisms**: Automatic restart on critical failures
- **Monitoring**: Error rates and types are logged for analysis

### Spark Streaming Resilience
- **Checkpointing**: Automatic state recovery after failures
- **Watermarking**: Handles late-arriving data gracefully
- **Backpressure**: Automatic rate limiting under high load
- **Resource Management**: Adaptive partition coalescing

## Configuration

### Environment Variables
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_SMOKE=smoke_stream

# Processing Configuration
WINDOW_DURATION=5 minutes
SLIDE_DURATION=1 minute
Z_SCORE_THRESHOLD=3.0
ROLLING_WINDOW_SIZE=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=stream_processing.log
```

### Tuning Parameters

#### For High Throughput
- Increase Kafka consumer `max.poll.records`
- Adjust Spark `spark.sql.streaming.minBatchesToRetain`
- Optimize checkpoint intervals

#### For Low Latency
- Reduce window slide duration
- Decrease Spark trigger intervals
- Minimize checkpoint frequency

#### For Memory Optimization
- Reduce rolling window size
- Adjust Spark executor memory
- Optimize watermark duration

## Monitoring and Debugging

### Health Checks
```bash
# Check Kafka consumer lag
docker exec -it smoke_kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group smoke_detection_group

# Monitor processing logs
tail -f stream_processing.log

# Check Spark streaming status
curl http://localhost:4040/api/v1/applications
```

### Performance Metrics
- **Throughput**: Messages processed per second
- **Latency**: End-to-end processing time
- **Error Rate**: Percentage of failed messages
- **Alert Rate**: Anomalies detected per time window

### Troubleshooting

#### Common Issues
1. **Kafka Connection Failed**: Check if Kafka is running and accessible
2. **High Memory Usage**: Reduce window size or increase heap memory
3. **Processing Lag**: Scale up consumers or optimize processing logic
4. **Missing Dependencies**: Ensure all Python packages are installed

#### Debug Commands
```bash
# Test Kafka connectivity
docker exec -it smoke_kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic smoke_stream

# Check data format
python -c "from data_processing.stream_processing.error_handler import validate_sensor_data; print('Validation OK')"

# Verify anomaly detection
python -c "from data_processing.stream_processing.detect_anomalies import detect_anomalies; print('Detection OK')"
```

## Dependencies

### Python Packages
- `kafka-python`: Kafka client library
- `pyspark`: Apache Spark for Python
- `numpy`: Numerical computing
- `pandas`: Data manipulation (optional)

### System Requirements
- **Memory**: Minimum 4GB RAM for Spark
- **CPU**: Multi-core recommended for parallel processing
- **Storage**: SSD recommended for checkpoint performance
- **Network**: Stable connection to Kafka cluster
