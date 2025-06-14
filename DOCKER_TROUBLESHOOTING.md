# 🔧 Docker Troubleshooting Guide

## Quick Fix Summary

**❌ Original Issue**: `docker-compose up --build` fails due to dependency conflicts

**✅ Solution**: Use the updated files and startup scripts provided

## 🚀 Recommended Startup Methods

### Option 1: Use Startup Script (Recommended)

**Windows:**
```powershell
.\start_system.ps1
```

**Linux/Mac:**
```bash
chmod +x start_system.sh
./start_system.sh
```

### Option 2: Manual Docker Compose

```bash
# Clean up first
docker-compose down --remove-orphans

# Build with fixed requirements
docker-compose build

# Start services in order
docker-compose up -d zookeeper kafka postgres
sleep 30
docker-compose up -d smoke_kafka_producer stream_processor
sleep 20
docker-compose up -d ml_trainer flask_api
sleep 30
docker-compose up -d spark_stream_processor prometheus grafana metrics_simulator
```

## 🔍 Common Issues & Solutions

### 1. **google-re2 Compilation Failure**
```
ERROR: Failed building wheel for google-re2
_re2.cc:15:10: fatal error: absl/strings/string_view.h: No such file or directory
```

**Solution**: Updated Dockerfiles now use `requirements_docker.txt` which excludes problematic packages.

### 2. **Flask Version Conflicts**
```
ERROR: apache-airflow 2.10.5 has requirement flask<2.3,>=2.2.1, but you'll have flask 3.0.3
```

**Solution**: Fixed in `requirements_docker.txt` with Flask 2.2.5 and compatible versions.

### 3. **py4j Version Mismatch**
```
ERROR: pyspark 3.5.6 has requirement py4j==0.10.9.7, but you'll have py4j 0.10.9.9
```

**Solution**: Fixed with exact version `py4j==0.10.9.7` in requirements.

### 4. **Memory Issues During Build**
```
ERROR: Command errored out with exit status 137
```

**Solution**: 
- Increase Docker memory allocation to 4GB+
- Use `requirements_docker.txt` with pre-compiled packages

### 5. **Service Startup Order Issues**
```
ERROR: Connection refused to kafka:9092
```

**Solution**: Use the startup scripts which handle proper service ordering.

## 📋 Verification Steps

### 1. Check Service Status
```bash
docker-compose ps
```

### 2. Check Individual Service Logs
```bash
# Check specific service
docker-compose logs flask_api

# Follow logs in real-time
docker-compose logs -f ml_trainer
```

### 3. Test API Endpoints
```bash
# Health check
curl http://localhost:5000/health

# Test prediction
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"temperature": 25.5, "humidity": 60.0, "smoke": 0.1}'
```

### 4. Access Web Interfaces
- **Flask API**: http://localhost:5000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Airflow**: http://localhost:8080 (admin/admin)
- **Spark UI**: http://localhost:4040

## 🛠️ Emergency Fixes

### If Everything Fails
```bash
# Nuclear option - clean everything
docker-compose down -v --remove-orphans
docker system prune -a -f
docker volume prune -f

# Start fresh
docker-compose build --no-cache
./start_system.sh
```

### If Specific Service Fails
```bash
# Restart individual service
docker-compose restart flask_api

# Rebuild specific service
docker-compose build --no-cache flask_api
docker-compose up -d flask_api
```

### If Dependencies Still Fail
```bash
# Use minimal requirements
pip install flask==2.2.5 pandas==2.0.3 scikit-learn==1.3.2 kafka-python==2.0.2

# Or use the installation script
python install_dependencies.py
```

## 📊 Performance Optimization

### For Faster Builds
1. Use `requirements_docker.txt` (fixed versions)
2. Enable Docker BuildKit: `export DOCKER_BUILDKIT=1`
3. Use multi-stage builds (already implemented)

### For Better Runtime Performance
1. Increase Docker memory to 6GB+
2. Use SSD storage for Docker volumes
3. Limit concurrent service starts

## 🔄 Alternative Approaches

### 1. Use Pre-built Images
Consider using official images where possible:
- `confluentinc/cp-kafka` ✅ (already used)
- `postgres:15` ✅ (already used)
- `apache/spark:3.4.0-python3` ✅ (already used)

### 2. Separate Environments
Run problematic services separately:
```bash
# Run Airflow separately
docker run -p 8080:8080 apache/airflow:2.7.1-python3.10

# Run core services only
docker-compose up -d zookeeper kafka postgres flask_api
```

### 3. Use Virtual Environments
For development:
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements_fixed.txt
```

## 📞 Getting Help

If you're still having issues:

1. **Check the logs**: `docker-compose logs [service_name]`
2. **Verify requirements**: Ensure you're using `requirements_docker.txt`
3. **Check system resources**: Ensure adequate memory/disk space
4. **Try minimal setup**: Start with just core services first

## ✅ Success Indicators

You'll know it's working when:
- All services show "Up" in `docker-compose ps`
- Flask API responds at http://localhost:5000/health
- Grafana loads at http://localhost:3000
- No error messages in logs
- ML model training completes successfully
