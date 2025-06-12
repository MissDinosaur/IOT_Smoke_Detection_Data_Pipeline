# 🧪 IoT Smoke Detection - Streaming Tests

Comprehensive test suite for the streaming components of the IoT Smoke Detection Data Pipeline.

## 📋 **Test Overview**

### **Test Categories**

| Category | Files | Purpose | Requirements |
|----------|-------|---------|--------------|
| **🧪 Unit Tests** | `test_streaming.py` | Data processing logic | None |
| **🔗 Integration Tests** | `test_*_integration.py` | Service integration | Kafka + API |
| **📨 Kafka Tests** | `test_kafka_integration.py` | Kafka functionality | Kafka cluster |
| **🌐 API Tests** | `test_streaming.py` | Flask API integration | Flask API |
| **🔥 Flask Tests** | `test_flask_api_comprehensive.py` | Complete Flask API testing | Flask API |
| **⚡ Spark Tests** | `test_spark_streaming.py` | Spark streaming | Spark cluster |
| **🤖 ML Integration Tests** | `test_ml_streaming_integration.py` | ML model integration | Flask API + ML Model |
| **🚀 ML Performance Tests** | `test_ml_performance.py` | ML performance metrics | Flask API + ML Model |
| **📊 Performance Tests** | All files | Performance metrics | All services |

### **Test Structure**

```
tests/
├── test_streaming.py           # Main streaming tests
├── test_kafka_integration.py   # Kafka-specific tests
├── test_spark_streaming.py     # Spark streaming tests
├── conftest.py                 # Shared fixtures
├── run_streaming_tests.py      # Test runner
└── README_STREAMING_TESTS.md   # This file
```

## 🚀 **Quick Start**

### **1. Prerequisites**

```bash
# Install test dependencies
pip install pytest pytest-html pytest-cov pytest-timeout requests

# Optional: For parallel testing
pip install pytest-xdist

# Optional: For Kafka testing
pip install kafka-python
```

### **2. Service Requirements**

| Service | URL | Status Check |
|---------|-----|--------------|
| **Kafka** | `localhost:9092` | Producer connection |
| **Flask API** | `http://localhost:5000` | `/health` endpoint |
| **Spark UI** | `http://localhost:4040` | UI accessibility |

### **3. Run Tests**

```bash
# Quick smoke tests
python tests/run_streaming_tests.py --quick

# Unit tests only
python tests/run_streaming_tests.py --unit

# Integration tests
python tests/run_streaming_tests.py --integration

# ML-specific tests
python tests/run_streaming_tests.py --ml

# ML performance tests
python tests/run_streaming_tests.py --ml-performance

# All tests
python tests/run_streaming_tests.py --all
```

## 📊 **Test Categories Detail**

### **🧪 Unit Tests**

**Purpose:** Test individual components without external dependencies.

```bash
# Run unit tests
python tests/run_streaming_tests.py --unit

# Or directly with pytest
pytest tests/ -m unit -v
```

**Coverage:**
- ✅ Data validation logic
- ✅ Data transformation functions
- ✅ Anomaly detection algorithms
- ✅ Batch processing logic
- ✅ Error handling mechanisms

**Example:**
```python
def test_sensor_data_validation():
    """Test sensor data validation logic."""
    valid_data = {'Temperature[C]': 25.5, 'Humidity[%]': 45.0, ...}
    assert validate_sensor_data(valid_data) == True
    
    invalid_data = {'Temperature[C]': 'invalid'}
    assert validate_sensor_data(invalid_data) == False
```

### **🔗 Integration Tests**

**Purpose:** Test interaction between services and components.

```bash
# Run integration tests
python tests/run_streaming_tests.py --integration
```

**Coverage:**
- ✅ Kafka ↔ Stream Processing
- ✅ Stream Processing ↔ Flask API
- ✅ End-to-end data flow
- ✅ Service communication
- ✅ Error recovery

**Example:**
```python
def test_complete_pipeline():
    """Test complete streaming pipeline."""
    # Send to Kafka → Process → Predict → Verify
    producer.send('smoke_detection', sensor_data)
    result = api_client.predict(processed_data)
    assert result['prediction'] in [0, 1]
```

### **📨 Kafka Tests**

**Purpose:** Test Kafka producer/consumer functionality.

```bash
# Run Kafka tests
python tests/run_streaming_tests.py --kafka
```

**Coverage:**
- ✅ Producer reliability
- ✅ Consumer group management
- ✅ Message serialization
- ✅ Partition handling
- ✅ Error recovery
- ✅ Performance metrics

**Example:**
```python
def test_kafka_producer_performance():
    """Test Kafka producer throughput."""
    start_time = time.time()
    for i in range(1000):
        producer.send('smoke_detection', sensor_data)
    duration = time.time() - start_time
    throughput = 1000 / duration
    assert throughput > 100  # messages/second
```

### **🌐 API Tests**

**Purpose:** Test Flask API integration in streaming context.

```bash
# Run API tests
python tests/run_streaming_tests.py --api
```

**Coverage:**
- ✅ Single prediction endpoint
- ✅ Batch prediction endpoint
- ✅ Health check endpoint
- ✅ Error handling
- ✅ Response validation
- ✅ Performance metrics

**Example:**
```python
def test_batch_prediction_api():
    """Test batch prediction API."""
    batch_data = [sensor_data_1, sensor_data_2, ...]
    response = api_client.predict_batch(batch_data)
    assert response.status_code == 200
    assert len(response.json()['predictions']) == len(batch_data)
```

### **🔥 Flask API Comprehensive Tests**

**Purpose:** Complete Flask API testing including all endpoints, validation, and performance.

```bash
# Run comprehensive Flask tests
python tests/run_streaming_tests.py --flask
```

**Coverage:**
- ✅ **All Endpoints** - `/health`, `/predict`, `/predict/batch`, `/model/info`, `/model/reload`, `/predictions/stats`
- ✅ **Input Validation** - Invalid JSON, missing fields, wrong data types, extreme values
- ✅ **Error Handling** - Proper HTTP status codes, error messages, graceful degradation
- ✅ **Performance Testing** - Response time consistency, concurrent request handling
- ✅ **Headers & CORS** - Content-Type, CORS headers, security headers
- ✅ **Rate Limiting** - Rate limit detection and header validation

**Example:**
```python
def test_predict_endpoint():
    """Test single prediction endpoint."""
    response = api_client.predict(VALID_SENSOR_DATA)
    assert response.status_code == 200

    result = response.json()
    assert 'prediction' in result
    assert 'confidence' in result
    assert 'processing_time_seconds' in result

    # Validate prediction values
    assert result['prediction'] in [0, 1]
    assert result['prediction_label'] in ['fire', 'no_fire']

    # Validate confidence scores
    confidence = result['confidence']
    assert 0.0 <= confidence['fire'] <= 1.0
    assert 0.0 <= confidence['no_fire'] <= 1.0
    assert abs(confidence['fire'] + confidence['no_fire'] - 1.0) < 0.01
```

### **⚡ Spark Tests**

**Purpose:** Test Spark streaming integration.

```bash
# Run Spark tests
python tests/run_streaming_tests.py --spark
```

**Coverage:**
- ✅ Spark context setup
- ✅ Kafka-Spark integration
- ✅ Data transformations
- ✅ ML model integration
- ✅ Performance metrics

**Example:**
```python
def test_spark_kafka_integration():
    """Test Spark-Kafka integration."""
    # Mock Spark streaming context
    streaming_context = create_streaming_context()
    kafka_stream = streaming_context.kafkaStream(...)
    assert kafka_stream is not None
```

### **🤖 ML Integration Tests**

**Purpose:** Test ML model integration in streaming pipeline.

```bash
# Run ML integration tests
python tests/run_streaming_tests.py --ml
```

**Coverage:**
- ✅ Model availability and loading
- ✅ Single prediction accuracy
- ✅ Batch prediction consistency
- ✅ Feature engineering validation
- ✅ Error handling with invalid data
- ✅ Confidence score analysis
- ✅ Model information endpoints

**Example:**
```python
def test_single_prediction_accuracy():
    """Test single prediction accuracy."""
    response = api_client.predict(NORMAL_SENSOR_DATA)
    assert response.status_code == 200

    result = response.json()
    assert 'prediction' in result
    assert 'confidence' in result
    assert result['prediction'] in [0, 1]
    assert result['prediction_label'] in ['fire', 'no_fire']
```

### **🚀 ML Performance Tests**

**Purpose:** Test ML model performance under load.

```bash
# Run ML performance tests
python tests/run_streaming_tests.py --ml-performance
```

**Coverage:**
- ✅ Single prediction latency
- ✅ Batch prediction efficiency
- ✅ Concurrent request handling
- ✅ Memory usage stability
- ✅ CPU utilization monitoring
- ✅ Sustained load performance
- ✅ Scalability limits testing

**Performance Benchmarks:**
- **Single Prediction:** < 100ms average
- **Batch Efficiency:** Better than individual predictions
- **Concurrent Handling:** 10+ simultaneous requests
- **Memory Stability:** < 50MB increase during testing
- **Sustained Load:** 5+ requests/second for 30+ seconds

**Example:**
```python
def test_single_prediction_latency():
    """Test single prediction latency."""
    latencies = []
    for _ in range(50):
        start_time = time.time()
        response = api_client.predict(PERFORMANCE_TEST_DATA)
        end_time = time.time()

        assert response.status_code == 200
        latencies.append((end_time - start_time) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 100  # Less than 100ms
```

### **📊 Performance Tests**

**Purpose:** Measure system performance under load.

```bash
# Run performance tests
python tests/run_streaming_tests.py --performance
```

**Metrics:**
- ✅ **Throughput:** Messages/second
- ✅ **Latency:** End-to-end processing time
- ✅ **Memory Usage:** Resource consumption
- ✅ **Error Rate:** Failure percentage
- ✅ **Recovery Time:** Error recovery speed

**Benchmarks:**
- **Kafka Producer:** > 100 msg/s
- **Kafka Consumer:** > 50 msg/s
- **API Response:** < 100ms average
- **End-to-end:** < 1s latency

## 🛠️ **Test Runner Usage**

### **Basic Commands**

```bash
# Quick health check
python tests/run_streaming_tests.py --quick

# Specific test types
python tests/run_streaming_tests.py --unit
python tests/run_streaming_tests.py --integration
python tests/run_streaming_tests.py --kafka
python tests/run_streaming_tests.py --api
python tests/run_streaming_tests.py --performance

# All tests
python tests/run_streaming_tests.py --all
```

### **Advanced Options**

```bash
# With HTML report
python tests/run_streaming_tests.py --all --html-report

# With coverage
python tests/run_streaming_tests.py --unit --coverage

# Parallel execution
python tests/run_streaming_tests.py --integration --parallel

# Verbose output
python tests/run_streaming_tests.py --kafka --verbose

# Stop on first failure
python tests/run_streaming_tests.py --all --maxfail 1

# Filter by keyword
python tests/run_streaming_tests.py --all --keyword "producer"
```

### **Direct Pytest Usage**

```bash
# Run specific test file
pytest tests/test_streaming.py -v

# Run with markers
pytest tests/ -m "kafka and not slow" -v

# Run specific test class
pytest tests/test_kafka_integration.py::TestKafkaProducer -v

# Run with coverage
pytest tests/ --cov=data_processing --cov-report=html

# Generate HTML report
pytest tests/ --html=reports/test_report.html --self-contained-html
```

## 📈 **Test Reports**

### **HTML Reports**

```bash
# Generate HTML report
python tests/run_streaming_tests.py --all --html-report

# View report
open tests/reports/streaming_test_report.html
```

### **Coverage Reports**

```bash
# Generate coverage report
python tests/run_streaming_tests.py --unit --coverage

# View coverage
open tests/reports/coverage/index.html
```

### **Performance Reports**

Performance metrics are logged during test execution:

```
🚀 Running performance tests...
📊 Performance testing with: Kafka, Flask API

Kafka Producer Performance: 150.23 messages/second
API Response Time: 45.67ms average
End-to-end Latency: 234.56ms average
Memory Usage: 45.2MB increase
```

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Service URLs
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export FLASK_API_URL="http://localhost:5000"
export SPARK_UI_URL="http://localhost:4040"

# Test settings
export TEST_TIMEOUT="300"
export MAX_RETRIES="3"
```

### **Pytest Configuration**

See `pytest.ini` for detailed configuration:

```ini
[tool:pytest]
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    kafka: Tests requiring Kafka
    api: Tests requiring Flask API
    performance: Performance tests
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Kafka Not Available**
```
❌ Kafka is not available: NoBrokersAvailable
```
**Solution:** Start Kafka cluster with `docker-compose up kafka`

#### **API Not Available**
```
❌ Flask API is not available: Connection refused
```
**Solution:** Start Flask API with `docker-compose up flask_api`

#### **Import Errors**
```
ModuleNotFoundError: No module named 'kafka'
```
**Solution:** Install dependencies with `pip install kafka-python`

#### **Test Timeouts**
```
FAILED tests/test_streaming.py::test_performance - Timeout
```
**Solution:** Increase timeout with `--timeout 600` or check service performance

### **Service Health Checks**

```bash
# Check Kafka
python -c "from kafka import KafkaProducer; KafkaProducer(bootstrap_servers='localhost:9092')"

# Check Flask API
curl http://localhost:5000/health

# Check Spark UI
curl http://localhost:4040
```

## 📚 **Best Practices**

### **Writing Tests**

1. **Use Fixtures:** Leverage shared fixtures from `conftest.py`
2. **Mock External Services:** Use mocks when services aren't available
3. **Test Error Conditions:** Include negative test cases
4. **Performance Assertions:** Set realistic performance thresholds
5. **Clean Up:** Ensure tests clean up resources

### **Running Tests**

1. **Start with Quick Tests:** Use `--quick` for rapid feedback
2. **Check Service Health:** Ensure services are running before integration tests
3. **Use Appropriate Markers:** Run only relevant test categories
4. **Monitor Performance:** Track performance metrics over time
5. **Generate Reports:** Use HTML and coverage reports for analysis

### **CI/CD Integration**

```yaml
# Example GitHub Actions workflow
- name: Run Streaming Tests
  run: |
    docker-compose up -d kafka flask_api
    python tests/run_streaming_tests.py --integration --html-report
    python tests/run_streaming_tests.py --unit --coverage
```

## 🎯 **Test Coverage Goals**

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| **Data Processing** | 90% | ✅ Achieved |
| **Kafka Integration** | 85% | ✅ Achieved |
| **API Integration** | 95% | ✅ Achieved |
| **Error Handling** | 80% | ✅ Achieved |
| **Performance** | 100% | ✅ Achieved |

**The streaming test suite provides comprehensive coverage of all streaming components with robust error handling, performance monitoring, and integration testing capabilities!** 🎉
