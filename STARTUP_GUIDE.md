# 🚀 IoT Smoke Detection Pipeline - Complete Deployment Guide

This comprehensive guide ensures the **complete end-to-end enterprise-grade pipeline** runs successfully with full automation, monitoring, and ML capabilities.

## 📋 Prerequisites

### **Required Software**
- ✅ **Docker Desktop** (latest version)
- ✅ **Docker Compose** (included with Docker Desktop)
- ✅ **Git** (for cloning the repository)

### **System Requirements**
- **Memory**: 8GB RAM minimum (16GB recommended for optimal performance)
- **Storage**: 15GB free space (includes models, logs, and data)
- **Network**: Internet connection for downloading dependencies
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)

### **Architecture Support**
- **x86_64**: Full support for all features
- **ARM64/M1**: Compatible with performance optimizations

## 🔧 Pre-Flight Checklist

### **1. Verify Required Files**
Ensure these files exist in your project directory:
```
✅ docker-compose.yml
✅ .env
✅ data/smoke_detection_iot.csv
✅ requirements.txt
✅ Dockerfile.spark
```

### **2. Check Environment Configuration**
Verify your `.env` file contains:
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_PORT=9092
KAFKA_TOPIC_SMOKE=smoke_sensor_data

# Database Configuration  
POSTGRES_DB=smoke_detection
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Airflow Configuration
AIRFLOW_UID=50000
```

### **3. Verify Data Files**
Check that the main dataset exists:
```bash
# Windows
dir data\smoke_detection_iot.csv

# Linux/Mac
ls -la data/smoke_detection_iot.csv
```

## 🚀 Starting the Pipeline

### **Step 1: Build and Start All Services**
```bash
# Start the complete pipeline
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### **Step 2: Wait for Services to Initialize**
The pipeline takes 3-4 minutes to fully start. Services start in this order:
1. **PostgreSQL** (database)
2. **Zookeeper** (Kafka dependency)
3. **Kafka** (message broker)
4. **ML Trainer** (automatic model training)
5. **ML API** (ML prediction service)
6. **Kafka Producer** (data ingestion)
7. **Stream Processors** (real-time analytics)
8. **Spark Streaming** (ML-enhanced analytics via API)
9. **Airflow** (batch processing)

### **Step 3: Verify Everything is Running**
```bash
# Windows
scripts\verify_end_to_end.bat

# Linux/Mac
./scripts/verify_end_to_end.sh
```

## 📊 Expected Service Status

After successful startup, you should see:

```
CONTAINER NAME           STATUS              PORTS
smoke_postgres          Up 3 minutes        5432/tcp
smoke_zookeeper         Up 3 minutes        2181/tcp
smoke_kafka             Up 3 minutes        9092/tcp
ml_trainer              Up 2 minutes
ml_api                  Up 2 minutes        5000/tcp
kafka_producer          Up 1 minute
stream_processor        Up 1 minute
spark_stream_processor  Up 1 minute         4040/tcp
airflow                 Up 1 minute         8080/tcp
```

## 🌐 Web Interfaces

Once running, access these interfaces:

### **Spark UI** - Real-time Stream Processing
- **URL**: http://localhost:4040
- **Purpose**: Monitor Spark streaming jobs, performance metrics
- **Features**: Job progress, stage details, executor metrics

### **ML API** - Machine Learning Service
- **URL**: http://localhost:5000
- **Purpose**: ML model predictions and health monitoring
- **Endpoints**: `/health`, `/predict`, `/model/info`

### **Airflow UI** - Batch Processing
- **URL**: http://localhost:8080
- **Credentials**: admin / admin
- **Purpose**: Monitor and manage batch processing workflows

## 📈 Pipeline Components

### **1. Data Ingestion** ✅ (Untouched)
- **Service**: `kafka_producer`
- **Function**: Reads CSV data and streams to Kafka
- **Status**: Original implementation preserved

### **2. Stream Processing** ✅ (Enhanced)
- **Services**: `stream_processor`, `spark_stream_processor`
- **Function**: Real-time analytics with ML predictions
- **Features**: 
  - Statistical analytics
  - Threshold-based alerts
  - ML-based fire detection
  - Data quality monitoring

### **3. ML Integration** ✅ (New)
- **Function**: Real-time and historical ML predictions
- **Features**:
  - Trained model loading
  - Real-time predictions on streaming data
  - Historical data batch processing
  - Performance metrics tracking

### **4. Batch Processing** ✅ (Untouched)
- **Service**: `airflow`
- **Function**: Scheduled batch processing workflows
- **Status**: Original implementation preserved

## 🔍 Troubleshooting

### **Common Issues and Solutions**

#### **1. Services Not Starting**
```bash
# Check Docker status
docker info

# Check available memory
docker system df

# Restart Docker Desktop if needed
```

#### **2. Port Conflicts**
If ports 4040 or 8080 are in use:
```bash
# Check what's using the ports
netstat -an | findstr ":4040"
netstat -an | findstr ":8080"

# Stop conflicting services or change ports in docker-compose.yml
```

#### **3. ML Models Missing**
```bash
# Check ML models directory
ls ml/models/

# If empty, the pipeline will run without ML predictions
# Train models using:
python ml/training/train_model.py --data data/smoke_detection_iot.csv
```

#### **4. Memory Issues**
```bash
# Increase Docker memory allocation in Docker Desktop settings
# Recommended: 8GB minimum, 16GB preferred

# Or reduce services by commenting out in docker-compose.yml
```

#### **5. Kafka Connection Issues**
```bash
# Check Kafka logs
docker logs smoke_kafka

# Restart Kafka if needed
docker-compose restart smoke_kafka
```

## 📋 Verification Checklist

After startup, verify these components:

- [ ] **PostgreSQL**: Database is accessible
- [ ] **Kafka**: Message broker is running and accepting connections
- [ ] **Data Ingestion**: Producer is sending messages to Kafka
- [ ] **Stream Processing**: Regular processor is consuming and processing data
- [ ] **Spark Streaming**: Spark processor is running with ML integration
- [ ] **ML Integration**: Models are loaded (or gracefully disabled if missing)
- [ ] **Airflow**: Web UI is accessible and DAGs are loaded
- [ ] **Web UIs**: Spark UI (4040) and Airflow UI (8080) are accessible

## 🔧 Useful Commands

### **Service Management**
```bash
# View all container status
docker-compose ps

# View logs for specific service
docker logs <container_name>

# Restart specific service
docker-compose restart <service_name>

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### **Monitoring**
```bash
# Follow logs in real-time
docker logs -f spark_stream_processor

# Check resource usage
docker stats

# View Kafka topics
docker exec smoke_kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### **ML Model Management**
```bash
# Check for ML models
ls ml/models/

# Train new models
python ml/training/train_model.py --data data/smoke_detection_iot.csv

# Process historical data with ML
python data_processing/stream_processing/historical_ml_processor.py \
    --input data/smoke_detection_iot.csv \
    --output results/
```

## ✅ Success Indicators

The pipeline is working correctly when you see:

1. **All containers running** without restart loops
2. **Spark UI accessible** at http://localhost:4040 showing active streaming jobs
3. **Airflow UI accessible** at http://localhost:8080 with loaded DAGs
4. **Stream processing logs** showing data processing and analytics
5. **ML predictions** (if models are available) or graceful fallback
6. **No critical errors** in container logs

## 🎯 Expected Output

### **Successful Stream Processing Logs:**
```
📊 Window Analytics (2024-01-15 10:00:00 - 2024-01-15 10:05:00):
Records: 1,247, Temp: 26.8°C (σ=2.3), Humidity: 52.1%
TVOC: 185.4ppb (max=245.0), PM2.5: 12.3μg/m³
Fire Alarms: 0, Quality: 95.2%, ML: No Fire (0.85)
```

### **ML Integration Status:**
```
✅ ML model loaded successfully:
   Type: RandomForestClassifier
   Features: 13
   Has Scaler: True
🤖 ML model integration enabled
```

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: `docker logs <container_name>`
2. **Run verification script**: `scripts/verify_end_to_end.bat` (Windows) or `./scripts/verify_end_to_end.sh` (Linux/Mac)
3. **Check system resources**: Ensure sufficient memory and disk space
4. **Restart services**: `docker-compose restart <service_name>`
5. **Full restart**: `docker-compose down && docker-compose up --build`

The pipeline is designed to be resilient and will continue working even if some components (like ML models) are missing. The core data ingestion and stream processing will always function! 🚀
