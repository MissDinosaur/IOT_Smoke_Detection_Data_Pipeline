# 🐳 Docker Configuration Files

This directory contains all Docker configuration files for the IoT Smoke Detection Data Pipeline project.

## 📁 **Docker Files Overview**

| File | Purpose | Base Image | Ports | Used By |
|------|---------|------------|-------|---------|
| **Dockerfile.api** | Flask API Backend | python:3.10-slim | 5000 | flask_api service |
| **Dockerfile.ml** | ML Training Service | python:3.10 | 5000 | ml_trainer service |
| **Dockerfile.spark** | Spark Stream Processor | apache/spark:3.4.0-python3 | 4040, 4041 | spark_stream_processor service |
| **Dockerfile.airflow** | Airflow Batch Processing | apache/airflow:2.7.1-python3.10 | 8080 | airflow service |
| **Dockerfile.stream** | Stream Processing | python:3.10 | - | stream_processor service |
| **Dockerfile.ingestion** | Data Ingestion | python:3.10 | - | smoke_kafka_producer service |
| **Dockerfile.metrics** | Metrics Simulation | python:3.10-slim | 8000 | metrics_simulator service |
| **Dockerfile.spark.bitnami** | Alternative Spark | bitnami/spark:3.4.1 | - | Alternative option |

## 🚀 **Service Descriptions**

### **🔥 Dockerfile.api**
**Flask API Backend - Central prediction service**
- **Purpose**: Provides REST API for smoke detection predictions
- **Features**: ML model loading, real-time predictions, health monitoring
- **Endpoints**: `/predict`, `/health`, `/model/info`, `/metrics`
- **Dependencies**: scikit-learn, flask, prometheus-client

### **🤖 Dockerfile.ml**
**ML Training Service - Automated model training**
- **Purpose**: Trains and generates ML models automatically
- **Features**: Auto-training, model versioning, pickle file generation
- **Schedule**: Trains models every 24 hours
- **Output**: Generates `best_model.pkl` for API consumption

### **⚡ Dockerfile.spark**
**Spark Stream Processor - Real-time analytics**
- **Purpose**: Processes streaming data from Kafka
- **Features**: Real-time analytics, ML integration, data transformation
- **Integration**: Calls Flask API for predictions
- **UI**: Spark Web UI available at port 4040

### **🔄 Dockerfile.airflow**
**Airflow Batch Processing - Workflow orchestration**
- **Purpose**: Manages batch processing workflows
- **Features**: DAG scheduling, task orchestration, data pipeline management
- **UI**: Airflow Web UI available at port 8080
- **Credentials**: admin/admin

### **🌊 Dockerfile.stream**
**Stream Processing - Data transformation**
- **Purpose**: Processes streaming data with Python
- **Features**: Kafka integration, data transformation, checkpointing
- **Alternative**: Lighter alternative to Spark for simple stream processing

### **📥 Dockerfile.ingestion**
**Data Ingestion - Kafka producer**
- **Purpose**: Ingests IoT sensor data into Kafka
- **Features**: CSV data reading, Kafka publishing, data simulation
- **Data Source**: Reads from `data/smoke_detection_iot.csv`

### **📊 Dockerfile.metrics**
**Metrics Simulation - Monitoring data**
- **Purpose**: Simulates metrics for monitoring and testing
- **Features**: Prometheus metrics generation, test data simulation
- **Integration**: Works with Prometheus and Grafana

## 🔧 **Build Context**

All Docker files use the **project root** as build context:
```yaml
build:
  context: .
  dockerfile: docker/Dockerfile.xxx
```

This allows access to:
- `requirements.txt` - Python dependencies
- `app/` - Application code
- `ml/` - Machine learning models
- `data/` - Data files
- `config/` - Configuration files

## 📦 **Common Dependencies**

All containers share the same `requirements.txt` file containing:
- **Core**: numpy, pandas, scikit-learn
- **Streaming**: kafka-python, pyspark
- **Web**: flask, gunicorn
- **Monitoring**: prometheus-client
- **Database**: psycopg2-binary, sqlalchemy

## 🏗️ **Build Order**

Recommended build order for dependencies:
1. **ml_trainer** - Generates models first
2. **flask_api** - Depends on ML models
3. **spark_stream_processor** - Depends on Flask API
4. **Other services** - Can build in parallel

## 🔍 **Health Checks**

Most containers include health checks:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:PORT/health || exit 1
```

## 🛡️ **Security**

All containers follow security best practices:
- **Non-root users**: Each service runs as dedicated user
- **Minimal base images**: Using slim/alpine variants where possible
- **Dependency scanning**: Regular updates of base images
- **Resource limits**: Configured in docker-compose.yml

## 🚀 **Usage**

### **Build All Services**
```bash
docker-compose build
```

### **Build Specific Service**
```bash
docker-compose build flask_api
```

### **Start All Services**
```bash
docker-compose up --build
```

### **Start Specific Service**
```bash
docker-compose up flask_api
```

## 🔧 **Development**

### **Local Development**
For local development, you can override Dockerfiles:
```yaml
# docker-compose.override.yml
services:
  flask_api:
    build:
      dockerfile: docker/Dockerfile.api.dev
    volumes:
      - ./app:/app/app:ro
```

### **Testing**
Each Dockerfile can be tested independently:
```bash
# Test Flask API
docker build -f docker/Dockerfile.api -t test-api .
docker run --rm -p 5000:5000 test-api

# Test ML Service
docker build -f docker/Dockerfile.ml -t test-ml .
docker run --rm test-ml
```

## 📝 **Maintenance**

### **Updating Dependencies**
1. Update `requirements.txt`
2. Rebuild all containers: `docker-compose build --no-cache`
3. Test all services: `docker-compose up`

### **Adding New Services**
1. Create new `Dockerfile.servicename`
2. Add service to `docker-compose.yml`
3. Update this README
4. Test integration

## 🆘 **Troubleshooting**

### **Common Issues**
- **Build failures**: Check `requirements.txt` compatibility
- **Port conflicts**: Ensure ports are available
- **Volume mounts**: Verify file paths exist
- **Dependencies**: Check service startup order

### **Debug Commands**
```bash
# Check container logs
docker-compose logs flask_api

# Enter container shell
docker-compose exec flask_api bash

# Rebuild without cache
docker-compose build --no-cache flask_api
```

## 📞 **Support**

For Docker-related issues:
1. Check container logs: `docker-compose logs [service]`
2. Verify health checks: `docker-compose ps`
3. Test individual containers: `docker build -f docker/Dockerfile.xxx`
4. Review this documentation

**All Docker configurations are production-ready and optimized for the IoT Smoke Detection Pipeline!** 🔥
