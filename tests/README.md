# Test Suite for IoT Smoke Detection Data Pipeline

This comprehensive test suite provides thorough testing coverage for both **Stream Processing** and **Machine Learning** components of the IoT smoke detection system.

## 📁 Test Structure

```
tests/
├── stream_processing/           # Stream processing tests
│   ├── test_error_handler.py   # Error handling and validation tests
│   └── test_metrics_streaming.py # Real-time analytics tests
├── ml/                         # Machine learning tests
│   ├── test_training.py        # Model training pipeline tests
│   └── test_inference.py       # Model inference and API tests
├── conftest.py                 # Shared fixtures and configuration
├── run_tests.py               # Comprehensive test runner
├── requirements-test.txt       # Test dependencies
└── README.md                  # This file
```

## 🎯 Test Categories

### **Stream Processing Tests**
- **Error Handler Tests** (`test_error_handler.py`)
  - Data validation and sanitization
  - Retry mechanisms with exponential backoff
  - Custom exception handling
  - Processing metrics and monitoring
  - Utility functions for type conversion

- **Metrics Streaming Tests** (`test_metrics_streaming.py`)
  - Rolling window analytics
  - Threshold detection and alerting
  - Anomaly detection algorithms
  - Real-time data aggregation
  - Performance monitoring

### **Machine Learning Tests**
- **Training Tests** (`test_training.py`)
  - Feature engineering functionality
  - Model configuration management
  - Training pipeline execution
  - Model evaluation and metrics
  - Error handling during training

- **Inference Tests** (`test_inference.py`)
  - Model loading and management
  - Single and batch predictions
  - Input validation and preprocessing
  - Flask API endpoints
  - Error handling and edge cases

## 🚀 Quick Start

### **1. Install Test Dependencies**
```bash
# Install test requirements
pip install -r tests/requirements-test.txt

# Or install specific testing tools
pip install pytest pytest-cov pytest-xdist
```

### **2. Run All Tests**
```bash
# Run all tests with coverage
python tests/run_tests.py --all --coverage

# Run tests in parallel for speed
python tests/run_tests.py --all --parallel
```

### **3. Run Specific Test Categories**
```bash
# Stream processing tests only
python tests/run_tests.py --stream

# Machine learning tests only
python tests/run_tests.py --ml

# Unit tests only (fast)
python tests/run_tests.py --unit

# Integration tests only
python tests/run_tests.py --integration
```

## 📊 Test Coverage

### **Stream Processing Coverage**
- ✅ **Data Validation**: 100% coverage of sensor data validation
- ✅ **Error Handling**: Complete retry mechanism testing
- ✅ **Metrics Calculation**: Rolling window analytics validation
- ✅ **Threshold Detection**: Alert system testing
- ✅ **Anomaly Detection**: Statistical anomaly algorithms

### **Machine Learning Coverage**
- ✅ **Feature Engineering**: Advanced feature creation testing
- ✅ **Model Training**: Complete pipeline validation
- ✅ **Model Evaluation**: Comprehensive metrics testing
- ✅ **Inference Pipeline**: Single and batch prediction testing
- ✅ **API Endpoints**: Flask API comprehensive testing

## 🔧 Test Runner Options

### **Basic Usage**
```bash
# Run all tests
python tests/run_tests.py

# Run with verbose output
python tests/run_tests.py --verbose

# Run specific test file
python tests/run_tests.py --file tests/ml/test_training.py
```

### **Advanced Options**
```bash
# Generate coverage report
python tests/run_tests.py --all --coverage

# Run fast tests only (exclude slow tests)
python tests/run_tests.py --fast

# Check test dependencies
python tests/run_tests.py --check-deps

# Generate test report
python tests/run_tests.py --report
```

### **Parallel Execution**
```bash
# Run tests in parallel for faster execution
python tests/run_tests.py --all --parallel

# Run specific category in parallel
python tests/run_tests.py --ml --parallel
```

## 📋 Test Examples

### **Stream Processing Test Examples**

#### **Data Validation Testing**
```python
def test_validate_sensor_data_valid_complete():
    """Test validation with complete valid sensor data."""
    valid_data = {
        "Temperature[C]": 25.5,
        "Humidity[%]": 45.2,
        "TVOC[ppb]": 150.0,
        # ... all required fields
    }
    
    is_valid, errors = validate_sensor_data(valid_data)
    assert is_valid is True
    assert len(errors) == 0
```

#### **Threshold Detection Testing**
```python
def test_detect_high_threshold_violations():
    """Test detection of high threshold violations."""
    high_data = {
        "Temperature[C]": 60.0,  # Above high threshold
        "TVOC[ppb]": 1500.0,     # Above high threshold
    }
    
    alerts = detector.detect_violations(high_data)
    assert len(alerts) > 0
    assert alerts[0]["level"] == AlertLevel.HIGH
```

### **Machine Learning Test Examples**

#### **Feature Engineering Testing**
```python
def test_create_advanced_features_basic():
    """Test basic advanced feature creation."""
    enhanced_data = feature_engineer.create_advanced_features(sample_data)
    
    # Should have more columns than original
    assert enhanced_data.shape[1] > sample_data.shape[1]
    
    # Check specific features
    assert "temp_squared" in enhanced_data.columns
    assert "humidity_log" in enhanced_data.columns
```

#### **Model Training Testing**
```python
def test_train_models_basic():
    """Test basic model training functionality."""
    results = trainer.train_models(X_train, X_test, y_train, y_test)
    
    assert "random_forest" in results
    assert "best_model" in results
    assert trainer.best_model is not None
```

#### **API Endpoint Testing**
```python
def test_flask_app_predict_endpoint():
    """Test Flask app prediction endpoint."""
    with app.test_client() as client:
        response = client.post('/predict', 
                             data=json.dumps(sample_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'prediction' in data
```

## 🎨 Test Fixtures

### **Shared Fixtures** (from `conftest.py`)
- `sample_sensor_data`: Standard sensor reading
- `fire_scenario_data`: Fire condition sensor data
- `sample_dataframe`: Pandas DataFrame with test data
- `trained_model`: Pre-trained ML model for testing
- `model_file`: Temporary model file
- `csv_data_file`: Temporary CSV data file
- `streaming_data_batch`: Batch of streaming data

### **Mock Objects**
- `mock_kafka_consumer`: Mock Kafka consumer
- `mock_kafka_producer`: Mock Kafka producer
- `TestDataGenerator`: Utility for generating test data

## 📈 Performance Testing

### **Benchmark Tests**
```bash
# Run performance benchmarks
python -m pytest tests/ --benchmark-only

# Generate benchmark report
python -m pytest tests/ --benchmark-json=benchmark.json
```

### **Memory Testing**
```bash
# Run with memory profiling
python -m pytest tests/ --profile

# Check for memory leaks
python -m pytest tests/ --memray
```

## 🔍 Test Debugging

### **Verbose Output**
```bash
# Detailed test output
python tests/run_tests.py --verbose

# Show test execution details
python -m pytest tests/ -v -s
```

### **Debug Specific Tests**
```bash
# Run single test with debugging
python -m pytest tests/ml/test_training.py::TestFeatureEngineer::test_create_advanced_features_basic -v -s

# Run with pdb debugging
python -m pytest tests/ --pdb
```

### **Test Coverage Analysis**
```bash
# Generate HTML coverage report
python tests/run_tests.py --all --coverage

# View coverage report
open tests/coverage_html/index.html
```

## 🚨 Continuous Integration

### **GitHub Actions Integration**
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements-test.txt
      - name: Run tests
        run: python tests/run_tests.py --all --coverage
```

### **Pre-commit Hooks**
```bash
# Install pre-commit
pip install pre-commit

# Set up pre-commit hooks
pre-commit install

# Run tests before commit
pre-commit run --all-files
```

## 📊 Test Metrics

### **Coverage Targets**
- **Stream Processing**: 95%+ coverage
- **Machine Learning**: 90%+ coverage
- **Overall Project**: 90%+ coverage

### **Performance Targets**
- **Unit Tests**: < 5 seconds total
- **Integration Tests**: < 30 seconds total
- **All Tests**: < 60 seconds total

### **Quality Metrics**
- **Test Success Rate**: 100%
- **Code Quality**: Flake8 compliant
- **Type Safety**: MyPy validated

## 🛠 Troubleshooting

### **Common Issues**

1. **Import Errors**
   ```bash
   # Ensure project root is in Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Missing Dependencies**
   ```bash
   # Check and install missing packages
   python tests/run_tests.py --check-deps
   ```

3. **Slow Tests**
   ```bash
   # Run only fast tests
   python tests/run_tests.py --fast
   ```

4. **Memory Issues**
   ```bash
   # Run tests with memory monitoring
   python -m pytest tests/ --memray
   ```

### **Debug Commands**
```bash
# Check test discovery
python -m pytest --collect-only

# Run with maximum verbosity
python -m pytest tests/ -vvv

# Show test durations
python -m pytest tests/ --durations=10
```

## 📚 Additional Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **Coverage.py Documentation**: https://coverage.readthedocs.io/
- **Testing Best Practices**: https://docs.python-guide.org/writing/tests/
- **Mock Testing**: https://docs.python.org/3/library/unittest.mock.html

## 🤝 Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` files, `test_*` functions
2. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
3. **Add docstrings**: Describe what the test validates
4. **Use fixtures**: Leverage shared fixtures from `conftest.py`
5. **Test edge cases**: Include error conditions and boundary values
6. **Update documentation**: Add test descriptions to this README

## 📝 Test Report Generation

```bash
# Generate comprehensive test report
python tests/run_tests.py --report

# View generated report
cat tests/test_report.md
```

The test suite provides comprehensive validation of the IoT smoke detection pipeline, ensuring reliability, performance, and correctness of both stream processing and machine learning components! 🎉
