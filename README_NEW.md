# 🔥 IoT Smoke Detection Data Pipeline

A **production-ready, enterprise-grade** real-time data pipeline for IoT smoke detection using Apache Kafka, Apache Spark, Machine Learning, and comprehensive automation.

## 🏗️ **Complete Architecture Overview**

This project implements a **comprehensive end-to-end ML-powered data pipeline** for processing IoT sensor data to detect smoke and fire incidents in real-time with full automation and monitoring.

### **🎯 Key Capabilities**
- ⚡ **Real-time Stream Processing** with sub-second latency
- 🤖 **Automated ML Pipeline** with training, deployment, and monitoring
- 📊 **Comprehensive Data Quality** monitoring and validation
- 🔄 **Self-Healing Architecture** with automatic recovery
- 📈 **Enterprise Monitoring** with alerts and reporting
- 🚀 **One-Command Deployment** with Docker Compose

## 🚀 **Quick Start**

### **Prerequisites**
- Docker Desktop (latest version)
- 8GB+ RAM (16GB recommended)
- 10GB+ free disk space

### **🎬 One-Command Setup**
```bash
# Clone and start the complete pipeline
git clone <repository-url>
cd IOT_Smoke_Detection_Data_Pipeline

# Start everything with one command
docker-compose up --build

# Verify deployment
scripts/verify_end_to_end.bat  # Windows
./scripts/verify_end_to_end.sh # Linux/Mac
```

### **🌐 Access Points**
- **Spark UI**: http://localhost:4040 (Real-time stream monitoring)
- **ML API**: http://localhost:5000 (Machine learning service)
- **Airflow UI**: http://localhost:8080 (Workflow management, admin/admin)

## 🏛️ **Microservices Architecture**

### **🔄 Core Services**
| Service | Purpose | Port | Health Check |
|---------|---------|------|--------------|
| **kafka** | Message broker | 9092 | Kafka topics |
| **kafka_producer** | Data ingestion | - | Message production |
| **stream_processor** | Basic analytics | - | Processing logs |
| **spark_stream_processor** | ML-enhanced analytics | 4040 | Spark UI |
| **ml_trainer** | Automatic model training | - | Model files |
| **ml_api** | ML prediction service | 5000 | `/health` endpoint |
| **airflow** | Workflow orchestration | 8080 | Airflow UI |
| **postgres** | Metadata storage | 5432 | Database connection |

### **📦 Container Dependencies**
```
postgres → airflow
zookeeper → kafka → kafka_producer
kafka → stream_processor
kafka → spark_stream_processor
ml_trainer → ml_api → spark_stream_processor
```

## 🤖 **Complete ML Pipeline**

### **🔄 Automated ML Lifecycle**
```
Data Collection → Quality Validation → Feature Engineering → Model Training → 
Validation → Deployment → Monitoring → Retraining → Performance Analysis
```

### **🎯 ML Components**
- **Training Service**: Automatic model training with validation
- **Prediction API**: Real-time ML inference service
- **Performance Monitoring**: Continuous model health tracking
- **Drift Detection**: Automatic model degradation detection
- **Model Management**: Versioning, deployment, and rollback

## 📅 **Automated Operations Schedule**

| Time | Operation | Frequency | Purpose |
|------|-----------|-----------|---------|
| **02:00** | ML Training | Daily | Model training & deployment |
| **06:00** | Batch Processing | Daily | Feature engineering & metrics |
| **Every 6h** | Data Quality Check | 4x Daily | Quality monitoring & alerts |
| **Every 12h** | Performance Monitor | 2x Daily | Model performance tracking |
| **Sun 03:00** | Historical Analysis | Weekly | Pattern discovery & insights |

## 🔧 **Configuration Management**

### **Environment Variables** (`.env`)
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_SMOKE=smoke_sensor_data

# ML Configuration
ML_AUTO_TRAIN_ON_STARTUP=true
ML_TRAINING_INTERVAL_HOURS=24
ML_API_URL=http://ml_api:5000

# Database Configuration
POSTGRES_DB=airflow
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow

# Airflow Configuration
AIRFLOW_UID=50000
AIRFLOW__CORE__EXECUTOR=LocalExecutor
```

## 📁 **Project Structure**

```
📦 IOT_Smoke_Detection_Data_Pipeline/
├── 📂 data_ingestion/              # Data ingestion layer
│   ├── 📂 stream/                  # Kafka producers
│   └── 📂 batch/                   # Batch data loaders
├── 📂 data_processing/             # Processing layer
│   ├── 📂 stream_processing/       # Real-time processing
│   │   ├── spark_streaming_processor.py
│   │   ├── historical_ml_processor.py
│   │   └── README_SPARK.md
│   └── 📂 batch_processing/        # Batch processing
│       ├── 📂 dags/               # Airflow DAGs
│       ├── 📂 tasks/              # Processing tasks
│       └── README_DAGS.md
├── 📂 ml/                         # Machine learning layer
│   ├── 📂 training/               # Model training
│   │   ├── train_model.py
│   │   ├── auto_trainer.py
│   │   └── README.md
│   ├── 📂 inference/              # Model inference
│   │   ├── predict_wrapper.py
│   │   ├── model_loader.py
│   │   └── README.md
│   └── 📂 models/                 # Trained models
├── 📂 config/                     # Configuration files
├── 📂 data/                       # Data storage
├── 📂 scripts/                    # Utility scripts
│   ├── verify_end_to_end.sh
│   └── verify_end_to_end.bat
├── 📄 docker-compose.yml          # Service orchestration
├── 📄 Dockerfile.spark            # Spark container
├── 📄 Dockerfile.ml               # ML services container
├── 📄 requirements.txt            # Python dependencies
├── 📄 STARTUP_GUIDE.md           # Deployment guide
└── 📄 README.md                   # This file
```

## 🔄 **Data Flow Architecture**

```
IoT Sensors → CSV Data → Kafka Producer → Apache Kafka
                                              ↓
                                    Stream Processors
                                    ├── Regular Analytics
                                    └── Spark + ML Analytics
                                              ↓
                                        ML Services
                                    ├── Auto Training
                                    └── Prediction API
                                              ↓
                                      Batch Processing
                                    ├── Quality Monitoring
                                    ├── Performance Tracking
                                    ├── Historical Analysis
                                    └── Model Management
                                              ↓
                                    Storage & Monitoring
                                    ├── PostgreSQL
                                    ├── Data Files
                                    └── Reports & Logs
```

## 🎯 **Key Features**

### **✅ Real-time Processing**
- Sub-second latency for critical alerts
- Windowed analytics (5-minute windows, 1-minute slides)
- 25+ statistical measures per window
- ML-enhanced fire detection

### **✅ Automated ML Pipeline**
- Automatic model training on startup
- Daily retraining with validation
- Real-time predictions via API
- Performance monitoring and drift detection

### **✅ Comprehensive Monitoring**
- Data quality validation every 6 hours
- Model performance tracking every 12 hours
- Historical analysis weekly
- Automated alert generation

### **✅ Enterprise Features**
- Fault-tolerant architecture
- Automatic service recovery
- Comprehensive logging and reporting
- Scalable microservices design

## 📊 **Expected Output**

### **Real-time Analytics**
```
📊 Window Analytics (2024-01-15 10:00:00 - 2024-01-15 10:05:00):
Records: 1,247, Temp: 26.8°C (σ=2.3), Humidity: 52.1%
TVOC: 185.4ppb (max=245.0), PM2.5: 12.3μg/m³
Fire Alarms: 0, Quality: 95.2%, ML: No Fire (0.85)
```

### **ML Training Results**
```
🤖 Starting automatic ML model training...
✅ Model saved: best_model.pkl
🎯 Training Results:
   Best Model: RandomForestClassifier
   Accuracy: 0.945
   Precision: 0.892
   Recall: 0.876
   F1-Score: 0.884
```

### **Service Health**
```
CONTAINER NAME           STATUS              PORTS
ml_trainer              Up 2 minutes        (Training Service)
ml_api                  Up 2 minutes        5000/tcp
spark_stream_processor  Up 1 minute         4040/tcp
airflow                 Up 1 minute         8080/tcp
```

## 🔍 **Monitoring & Alerting**

### **Data Quality Alerts**
- Critical: Overall quality score < 70%
- Warning: Anomaly rate > 10%
- Info: Completeness < 90% for any sensor

### **Model Performance Alerts**
- Critical: Model accuracy < 70%
- Warning: Response time > 5 seconds
- Info: Drift indicators detected

### **System Health Alerts**
- Critical: ML API not responding
- Warning: Training failures
- Info: Storage cleanup needed

## 📚 **Documentation**

- [🚀 Startup Guide](STARTUP_GUIDE.md) - Complete deployment instructions
- [⚡ Stream Processing](data_processing/stream_processing/README_SPARK.md) - Real-time analytics
- [🔄 Batch Processing](data_processing/batch_processing/README_DAGS.md) - Airflow DAGs
- [🤖 ML Training](ml/training/README.md) - Model training guide
- [🔮 ML API](ml/inference/README.md) - Prediction API documentation

## 🎉 **Benefits**

### **✅ Complete Automation**
- Zero manual intervention required
- Automatic model training and deployment
- Self-healing architecture
- Comprehensive monitoring

### **✅ Production Ready**
- Enterprise-grade reliability
- Scalable microservices architecture
- Comprehensive error handling
- Full observability

### **✅ ML-Powered**
- Real-time ML predictions
- Automatic model retraining
- Performance monitoring
- Drift detection

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🚀 Ready to deploy? Run `docker-compose up --build` and experience the complete IoT smoke detection pipeline!**
