# Spark Streaming Processor for IoT Smoke Detection

This comprehensive Spark streaming implementation provides production-ready real-time analytics for IoT smoke detection data with advanced features including multi-level alerting, data quality monitoring, and fault-tolerant processing.

## 🚀 Features

### **Core Streaming Analytics**
- **Real-time Data Processing**: Processes IoT sensor data from Kafka in real-time
- **Windowed Analytics**: Configurable time windows (5-minute windows, 1-minute slides by default)
- **Comprehensive Metrics**: 25+ statistical measures including averages, min/max, standard deviation, percentiles
- **Multi-sensor Support**: Handles all 14 sensor types from the Kaggle dataset

### **Machine Learning Integration**
- **Real-time ML Predictions**: Trained models predict fire/smoke on streaming data
- **Batch ML Processing**: Process historical data with ML models
- **Model Performance Tracking**: Monitor prediction accuracy and confidence
- **Prediction Caching**: Intelligent caching for improved performance
- **ML-based Alerting**: Enhanced alerts based on ML model predictions

### **Advanced Alerting System**
- **Multi-level Alerts**: Critical, High, and Low severity levels
- **Threshold-based Detection**: Configurable thresholds for all sensor types
- **Fire Alarm Integration**: Immediate critical alerts for fire alarm triggers
- **Alert History**: Maintains alert history with timestamps and context

### **Data Quality Monitoring**
- **Quality Scoring**: Real-time data quality assessment (0-100% score)
- **Anomaly Detection**: Statistical anomaly detection with Z-score analysis
- **Missing Data Detection**: Identifies and reports data gaps
- **Sensor Health Monitoring**: Detects stuck or malfunctioning sensors

### **Production Features**
- **Fault Tolerance**: Checkpointing and watermarking for exactly-once processing
- **Graceful Shutdown**: Signal handling for clean application termination
- **Performance Monitoring**: Processing time and resource usage tracking
- **Multiple Output Formats**: Console, Parquet files, and optional Kafka output

## 📁 File Structure

```
data_processing/stream_processing/
├── spark_streaming_processor.py    # Main Spark streaming application
├── README_SPARK.md                 # This documentation
└── test_spark_integration.py       # Integration tests

Root Directory:
├── Dockerfile.spark                # Spark container configuration
├── spark-defaults.conf            # Spark optimization settings
└── scripts/start_spark_streaming.sh # Production startup script
```

## 🔧 Configuration

### **StreamingConfig Class**
```python
@dataclass
class StreamingConfig:
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "smoke_sensor_data"
    window_duration: str = "5 minutes"
    slide_duration: str = "1 minute"
    watermark_delay: str = "10 minutes"
    checkpoint_location: str = "/app/data/checkpoints"
    output_path: str = "/app/data/processed_stream"
    enable_console_output: bool = True
    enable_file_output: bool = True
```

### **AlertThresholds Class**
```python
@dataclass
class AlertThresholds:
    temperature_high: float = 50.0
    temperature_critical: float = 80.0
    tvoc_high: float = 1000.0
    tvoc_critical: float = 2000.0
    pm25_high: float = 35.0
    pm25_critical: float = 75.0
    # ... additional thresholds
```

## 🚀 Quick Start

### **1. Using Docker Compose (Recommended)**
```bash
# Start the complete stack including Spark streaming
docker-compose up spark_stream_processor

# View Spark UI
open http://localhost:4040
```

### **2. Direct Python Execution**
```bash
# Basic execution with ML predictions
python3 data_processing/stream_processing/spark_streaming_processor.py

# With custom configuration and ML
python3 data_processing/stream_processing/spark_streaming_processor.py \
    --kafka-servers localhost:9092 \
    --window-duration "10 minutes" \
    --slide-duration "2 minutes" \
    --enable-console \
    --ml-model-path /app/ml/models/best_model.pkl

# Disable ML predictions
python3 data_processing/stream_processing/spark_streaming_processor.py \
    --disable-ml
```

### **3. Using Startup Script**
```bash
# Start with monitoring
./scripts/start_spark_streaming.sh start --enable-console

# Check status
./scripts/start_spark_streaming.sh status

# View logs
./scripts/start_spark_streaming.sh logs 100

# Stop gracefully
./scripts/start_spark_streaming.sh stop
```

### **4. Historical Data Processing with ML**
```bash
# Process historical CSV file with ML predictions
python3 data_processing/stream_processing/historical_ml_processor.py \
    --input data/historical_sensor_data.csv \
    --output results/historical_analysis \
    --model ml/models/best_model.pkl

# Process directory of CSV files
python3 data_processing/stream_processing/historical_ml_processor.py \
    --input data/historical/ \
    --output results/batch_analysis \
    --batch-size 5000 \
    --verbose

# Generate performance report
python3 data_processing/stream_processing/historical_ml_processor.py \
    --input data/test_data.csv \
    --output results/performance_test
```

## 📊 Analytics Output

### **Windowed Metrics**
The processor generates comprehensive analytics for each time window:

```
📊 Window Analytics (2024-01-15 10:00:00 - 2024-01-15 10:05:00):
Records: 1,247
Temp: 26.8°C (σ=2.3)
Humidity: 52.1%
TVOC: 185.4ppb (max=245.0)
PM2.5: 12.3μg/m³
Fire Alarms: 0
Quality: 95.2%
ML: No Fire (0.85)
```

### **Statistical Measures**
- **Basic Statistics**: Average, min, max for all sensors
- **Variability**: Standard deviation, variance
- **Distribution**: Median, 95th percentile
- **Counts**: Total records, fire alarms, null values
- **Quality**: Data completeness, anomaly flags

### **Alert Examples**
```
🚨 Critical temperature: 85.2°C in 2024-01-15 10:00:00 - 2024-01-15 10:05:00
⚠️  High TVOC level: 1,250.5 ppb in 2024-01-15 10:00:00 - 2024-01-15 10:05:00
🚨 Fire alarm triggered: 3 alarms in 2024-01-15 10:00:00 - 2024-01-15 10:05:00
🤖 ML FIRE PREDICTION: 0.92 confidence in 2024-01-15 10:00:00 - 2024-01-15 10:05:00 (Label: Fire Detected)
```

## 🏗 Architecture

### **Main Components**

1. **SparkStreamProcessor**: Main orchestration class
   - Manages Spark session lifecycle
   - Coordinates streaming pipeline
   - Handles multiple output streams

2. **AlertManager**: Multi-level alerting system
   - Evaluates sensor thresholds
   - Generates contextual alerts
   - Maintains alert history

3. **DataQualityMonitor**: Data quality assessment
   - Calculates quality scores
   - Identifies data issues
   - Monitors sensor health

### **Processing Pipeline**
```
Kafka Stream → JSON Parsing → Windowed Analytics → Alert Generation → Multiple Outputs
     ↓              ↓              ↓                    ↓              ↓
Raw Sensor    Structured     Statistical         Alert           Console/Files/
   Data         DataFrame      Measures          Messages         Kafka Output
```

## 🔍 Monitoring & Debugging

### **Spark UI**
- **URL**: http://localhost:4040
- **Features**: Job progress, stage details, executor metrics
- **Streaming Tab**: Batch processing times, input rates

### **Logging Levels**
```python
# Application logs
logger.info("📊 Window Analytics...")      # Analytics summary
logger.warning("⚠️ High TVOC Alert...")    # Threshold violations
logger.critical("🚨 Fire Alarm...")        # Critical alerts
logger.debug("Batch processed in 2.3s")    # Performance metrics
```

### **Health Checks**
```bash
# Docker health check
curl -f http://localhost:4040

# Application status
./scripts/start_spark_streaming.sh status

# Resource monitoring
docker stats spark_stream_processor
```

## ⚙️ Performance Tuning

### **Spark Configuration** (spark-defaults.conf)
```properties
# Memory allocation
spark.driver.memory                2g
spark.executor.memory              2g

# Streaming optimization
spark.sql.adaptive.enabled         true
spark.sql.adaptive.coalescePartitions.enabled  true

# Kafka integration
spark.sql.streaming.kafka.useDeprecatedOffsetFetching  false
```

### **Recommended Settings**
- **Window Duration**: 5-10 minutes for real-time analytics
- **Slide Duration**: 1-2 minutes for frequent updates
- **Watermark**: 10-15 minutes for late data handling
- **Checkpointing**: Every 30-60 seconds

## 🚨 Troubleshooting

### **Common Issues**

1. **Kafka Connection Failed**
   ```bash
   # Check Kafka availability
   docker logs kafka
   nc -z kafka 9092
   ```

2. **Out of Memory Errors**
   ```bash
   # Increase driver memory
   export SPARK_DRIVER_MEMORY=4g
   ```

3. **Checkpoint Recovery Issues**
   ```bash
   # Clear checkpoints (data loss!)
   rm -rf /app/data/checkpoints/*
   ```

4. **Slow Processing**
   ```bash
   # Check batch processing times in Spark UI
   # Increase parallelism or reduce window size
   ```

### **Debug Commands**
```bash
# View recent logs
./scripts/start_spark_streaming.sh logs 200

# Check container status
docker ps | grep spark

# Monitor resource usage
docker stats spark_stream_processor

# Access container shell
docker exec -it spark_stream_processor bash
```

## 🧪 Testing

### **Unit Tests**
```bash
# Run Spark integration tests
python -m pytest tests/stream_processing/test_metrics_streaming.py::TestSparkStreamingIntegration -v
```

### **Integration Testing**
```bash
# Test with sample data
python3 data_processing/stream_processing/spark_streaming_processor.py \
    --kafka-servers localhost:9092 \
    --enable-console \
    --window-duration "1 minute"
```

## 📈 Scaling Considerations

### **Horizontal Scaling**
- **Multiple Executors**: Increase `spark.executor.instances`
- **Partition Tuning**: Adjust `spark.sql.shuffle.partitions`
- **Resource Allocation**: Scale driver and executor memory

### **Vertical Scaling**
- **CPU Cores**: Increase `spark.executor.cores`
- **Memory**: Scale `spark.executor.memory` and `spark.driver.memory`
- **Network**: Optimize `spark.network.timeout` settings

## 🔐 Security

### **Basic Security**
- **Network Isolation**: Container-based networking
- **Resource Limits**: Memory and CPU constraints
- **Access Control**: Spark UI authentication (configurable)

### **Production Security**
- **SSL/TLS**: Enable for Kafka and Spark communication
- **Authentication**: Kerberos or custom authentication
- **Encryption**: Data encryption at rest and in transit

## 📚 Additional Resources

- **Spark Streaming Guide**: https://spark.apache.org/docs/latest/streaming-programming-guide.html
- **Kafka Integration**: https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html
- **Performance Tuning**: https://spark.apache.org/docs/latest/tuning.html
- **Monitoring**: https://spark.apache.org/docs/latest/monitoring.html

## 🤝 Contributing

When modifying the Spark streaming processor:

1. **Test Thoroughly**: Use both unit and integration tests
2. **Monitor Performance**: Check processing times and resource usage
3. **Update Documentation**: Keep this README current
4. **Follow Patterns**: Maintain consistent logging and error handling
5. **Validate Alerts**: Ensure alert thresholds are appropriate

The Spark streaming processor provides enterprise-grade real-time analytics for IoT smoke detection with comprehensive monitoring, alerting, and fault tolerance! 🎉
