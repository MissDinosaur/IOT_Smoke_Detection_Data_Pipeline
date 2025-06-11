"""
Pytest configuration and shared fixtures for the test suite.

This module provides:
- Common test fixtures
- Test configuration
- Shared test utilities
- Mock data generators
- Test environment setup
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import pickle
import json
from pathlib import Path
from unittest.mock import Mock, patch
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Test configuration
pytest_plugins = []


@pytest.fixture(scope="session")
def test_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="smoke_detection_tests_")
    yield Path(temp_dir)
    # Cleanup is handled by tempfile


@pytest.fixture
def sample_sensor_data():
    """Generate sample sensor data for testing."""
    return {
        "Temperature[C]": 25.5,
        "Humidity[%]": 45.2,
        "TVOC[ppb]": 150.0,
        "eCO2[ppm]": 450.0,
        "Raw H2": 12500,
        "Raw Ethanol": 18500,
        "Pressure[hPa]": 1013.25,
        "PM1.0": 5.2,
        "PM2.5": 8.1,
        "NC0.5": 1200,
        "NC1.0": 800,
        "NC2.5": 150,
        "CNT": 50,
        "Fire Alarm": 0
    }


@pytest.fixture
def fire_scenario_data():
    """Generate fire scenario sensor data for testing."""
    return {
        "Temperature[C]": 55.0,
        "Humidity[%]": 25.0,
        "TVOC[ppb]": 1500.0,
        "eCO2[ppm]": 1200.0,
        "Raw H2": 25000,
        "Raw Ethanol": 35000,
        "Pressure[hPa]": 1010.0,
        "PM1.0": 45.0,
        "PM2.5": 65.0,
        "NC0.5": 5000,
        "NC1.0": 3500,
        "NC2.5": 800,
        "CNT": 200,
        "Fire Alarm": 1
    }


@pytest.fixture
def sample_dataframe():
    """Generate sample DataFrame for testing."""
    np.random.seed(42)
    n_samples = 100
    
    return pd.DataFrame({
        "Temperature[C]": np.random.normal(25, 10, n_samples),
        "Humidity[%]": np.random.normal(50, 15, n_samples),
        "TVOC[ppb]": np.random.normal(200, 100, n_samples),
        "eCO2[ppm]": np.random.normal(500, 150, n_samples),
        "Raw H2": np.random.normal(15000, 5000, n_samples),
        "Raw Ethanol": np.random.normal(20000, 7000, n_samples),
        "Pressure[hPa]": np.random.normal(1013, 10, n_samples),
        "PM1.0": np.random.normal(8, 3, n_samples),
        "PM2.5": np.random.normal(12, 5, n_samples),
        "NC0.5": np.random.normal(1500, 500, n_samples),
        "NC1.0": np.random.normal(1000, 300, n_samples),
        "NC2.5": np.random.normal(200, 100, n_samples),
        "CNT": np.random.randint(0, 100, n_samples),
        "Fire Alarm": np.random.randint(0, 2, n_samples)
    })


@pytest.fixture
def trained_model():
    """Create a trained model for testing."""
    np.random.seed(42)
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    
    # Generate training data
    X = np.random.randn(100, 13)
    y = np.random.randint(0, 2, 100)
    
    # Train the model
    model.fit(X, y)
    
    return model


@pytest.fixture
def trained_scaler():
    """Create a trained scaler for testing."""
    np.random.seed(42)
    scaler = StandardScaler()
    
    # Generate training data
    X = np.random.randn(100, 13)
    
    # Fit the scaler
    scaler.fit(X)
    
    return scaler


@pytest.fixture
def feature_columns():
    """Standard feature columns for testing."""
    return [
        "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
        "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
        "NC0.5", "NC1.0", "NC2.5", "CNT"
    ]


@pytest.fixture
def model_file(trained_model, trained_scaler, feature_columns, test_data_dir):
    """Create a temporary model file for testing."""
    model_data = {
        "model": trained_model,
        "scaler": trained_scaler,
        "feature_columns": feature_columns,
        "metadata": {
            "model_type": "RandomForestClassifier",
            "training_date": "2024-01-01",
            "version": "1.0",
            "accuracy": 0.95
        }
    }
    
    model_path = test_data_dir / "test_model.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    yield str(model_path)
    
    # Cleanup
    if model_path.exists():
        model_path.unlink()


@pytest.fixture
def csv_data_file(sample_dataframe, test_data_dir):
    """Create a temporary CSV data file for testing."""
    csv_path = test_data_dir / "test_data.csv"
    sample_dataframe.to_csv(csv_path, index=False)
    
    yield str(csv_path)
    
    # Cleanup
    if csv_path.exists():
        csv_path.unlink()


@pytest.fixture
def invalid_sensor_data():
    """Generate invalid sensor data for testing error handling."""
    return {
        "Temperature[C]": "invalid_temperature",
        "Humidity[%]": -50.0,  # Out of range
        "TVOC[ppb]": None,
        "eCO2[ppm]": "not_a_number",
        "Raw H2": -1000,  # Negative value
        "Fire Alarm": "invalid_alarm"
    }


@pytest.fixture
def outlier_sensor_data():
    """Generate sensor data with extreme outliers for testing."""
    return {
        "Temperature[C]": 200.0,  # Extreme outlier
        "Humidity[%]": -100.0,    # Extreme outlier
        "TVOC[ppb]": -500.0,      # Negative outlier
        "eCO2[ppm]": 10000.0,     # High outlier
        "Raw H2": -5000,          # Negative outlier
        "Raw Ethanol": 1000000,   # Extreme high
        "Pressure[hPa]": 2000.0,  # Extreme outlier
        "PM1.0": -10.0,           # Negative
        "PM2.5": 500.0,           # Extreme high
        "NC0.5": -1000,           # Negative
        "NC1.0": 100000,          # Extreme high
        "NC2.5": -500,            # Negative
        "CNT": -100,              # Negative
        "Fire Alarm": 0
    }


@pytest.fixture
def batch_sensor_data(sample_sensor_data, fire_scenario_data):
    """Generate batch sensor data for testing."""
    return [
        sample_sensor_data,
        fire_scenario_data,
        {**sample_sensor_data, "Temperature[C]": 30.0},
        {**fire_scenario_data, "TVOC[ppb]": 2000.0}
    ]


@pytest.fixture
def mock_kafka_consumer():
    """Create a mock Kafka consumer for testing."""
    consumer = Mock()
    consumer.poll.return_value = {}
    consumer.subscribe.return_value = None
    consumer.close.return_value = None
    return consumer


@pytest.fixture
def mock_kafka_producer():
    """Create a mock Kafka producer for testing."""
    producer = Mock()
    producer.send.return_value = Mock()
    producer.flush.return_value = None
    producer.close.return_value = None
    return producer


@pytest.fixture
def streaming_data_batch():
    """Generate a batch of streaming data for testing."""
    import time
    current_time = time.time()
    
    return [
        {
            "Temperature[C]": 25.0 + i,
            "Humidity[%]": 50.0 - i,
            "TVOC[ppb]": 150.0 + i * 10,
            "eCO2[ppm]": 450.0 + i * 5,
            "Raw H2": 12500 + i * 100,
            "Raw Ethanol": 18500 + i * 150,
            "Pressure[hPa]": 1013.25 - i * 0.1,
            "PM1.0": 5.2 + i * 0.5,
            "PM2.5": 8.1 + i * 0.7,
            "NC0.5": 1200 + i * 50,
            "NC1.0": 800 + i * 30,
            "NC2.5": 150 + i * 10,
            "CNT": 50 + i,
            "Fire Alarm": 1 if i > 5 else 0,
            "timestamp": current_time + i
        }
        for i in range(10)
    ]


# Test utilities
class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def generate_sensor_reading(
        temperature_range=(20, 30),
        humidity_range=(40, 60),
        fire_alarm=0
    ):
        """Generate a single sensor reading with specified ranges."""
        return {
            "Temperature[C]": np.random.uniform(*temperature_range),
            "Humidity[%]": np.random.uniform(*humidity_range),
            "TVOC[ppb]": np.random.uniform(100, 300),
            "eCO2[ppm]": np.random.uniform(400, 600),
            "Raw H2": np.random.randint(10000, 20000),
            "Raw Ethanol": np.random.randint(15000, 25000),
            "Pressure[hPa]": np.random.uniform(1010, 1016),
            "PM1.0": np.random.uniform(3, 10),
            "PM2.5": np.random.uniform(5, 15),
            "NC0.5": np.random.randint(1000, 2000),
            "NC1.0": np.random.randint(700, 1300),
            "NC2.5": np.random.randint(100, 300),
            "CNT": np.random.randint(30, 80),
            "Fire Alarm": fire_alarm
        }
    
    @staticmethod
    def generate_time_series(
        length=100,
        fire_events=None
    ):
        """Generate time series sensor data."""
        if fire_events is None:
            fire_events = []
        
        data = []
        for i in range(length):
            fire_alarm = 1 if i in fire_events else 0
            
            if fire_alarm:
                # Fire conditions: high temp, low humidity, high TVOC
                reading = TestDataGenerator.generate_sensor_reading(
                    temperature_range=(50, 80),
                    humidity_range=(10, 30),
                    fire_alarm=fire_alarm
                )
                reading["TVOC[ppb]"] = np.random.uniform(1000, 2000)
                reading["PM2.5"] = np.random.uniform(30, 80)
            else:
                # Normal conditions
                reading = TestDataGenerator.generate_sensor_reading(
                    fire_alarm=fire_alarm
                )
            
            reading["timestamp"] = i
            data.append(reading)
        
        return data


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "ml: marks tests related to machine learning"
    )
    config.addinivalue_line(
        "markers", "stream: marks tests related to stream processing"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test file location
        if "test_training" in str(item.fspath) or "test_inference" in str(item.fspath):
            item.add_marker(pytest.mark.ml)
        
        if "stream_processing" in str(item.fspath):
            item.add_marker(pytest.mark.stream)
        
        # Mark slow tests
        if "test_complete_training_pipeline" in item.name:
            item.add_marker(pytest.mark.slow)
        
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
