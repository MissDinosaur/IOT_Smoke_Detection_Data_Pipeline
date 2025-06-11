"""
Comprehensive test cases for stream processing error handler.

This module tests all aspects of the error handling system including:
- Data validation functions
- Error handling mechanisms
- Retry decorators
- Sensor data sanitization
- Processing metrics
- Custom exceptions
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the modules to test
import sys
from pathlib import Path
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from data_processing.stream_processing.error_handler import (
    validate_sensor_data,
    sanitize_sensor_data,
    retry_on_kafka_error,
    handle_processing_error,
    log_processing_metrics,
    ProcessingMetrics,
    StreamProcessingError,
    DataValidationError,
    KafkaConnectionError,
    safe_float_conversion,
    safe_int_conversion,
    DEFAULT_SENSOR_VALUES,
    REQUIRED_SENSOR_FIELDS,
    NUMERIC_SENSOR_FIELDS
)
from kafka.errors import KafkaError, NoBrokersAvailable


class TestSensorDataValidation:
    """Test cases for sensor data validation functions."""
    
    def test_validate_sensor_data_valid_complete(self):
        """Test validation with complete valid sensor data."""
        valid_data = {
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
        
        is_valid, errors = validate_sensor_data(valid_data)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_sensor_data_missing_fields(self):
        """Test validation with missing required fields."""
        incomplete_data = {
            "Temperature[C]": 25.5,
            "Humidity[%]": 45.2
            # Missing other required fields
        }
        
        is_valid, errors = validate_sensor_data(incomplete_data)
        assert is_valid is False
        assert len(errors) > 0
        assert "Missing required fields" in errors[0]
    
    def test_validate_sensor_data_invalid_ranges(self):
        """Test validation with values outside valid ranges."""
        invalid_data = {
            "Temperature[C]": 150.0,  # Too high
            "Humidity[%]": -10.0,     # Too low
            "TVOC[ppb]": -50.0,       # Negative
            "eCO2[ppm]": 450.0,
            "Raw H2": 12500,
            "Raw Ethanol": 18500,
            "Pressure[hPa]": 500.0,   # Too low
            "PM1.0": -5.2,            # Negative
            "PM2.5": 8.1,
            "NC0.5": 1200,
            "NC1.0": 800,
            "NC2.5": 150,
            "CNT": 50,
            "Fire Alarm": 0
        }
        
        is_valid, errors = validate_sensor_data(invalid_data)
        assert is_valid is False
        assert len(errors) >= 4  # At least 4 range errors
        
        # Check specific error messages
        error_text = " ".join(errors)
        assert "Temperature out of range" in error_text
        assert "Humidity out of range" in error_text
        assert "Pressure out of range" in error_text
        assert "Negative" in error_text
    
    def test_validate_sensor_data_invalid_types(self):
        """Test validation with invalid data types."""
        invalid_types_data = {
            "Temperature[C]": "not_a_number",
            "Humidity[%]": None,
            "TVOC[ppb]": "invalid",
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
            "Fire Alarm": "invalid"
        }
        
        is_valid, errors = validate_sensor_data(invalid_types_data)
        assert is_valid is False
        assert len(errors) >= 3  # Type conversion errors
        
        error_text = " ".join(errors)
        assert "Invalid numeric value" in error_text
        assert "Invalid Fire Alarm value" in error_text
    
    def test_validate_fire_alarm_values(self):
        """Test Fire Alarm field validation with various values."""
        base_data = {field: 0.0 for field in REQUIRED_SENSOR_FIELDS if field != "Fire Alarm"}
        
        # Valid values
        for valid_value in [0, 1, "0", "1"]:
            data = base_data.copy()
            data["Fire Alarm"] = valid_value
            is_valid, errors = validate_sensor_data(data)
            assert is_valid is True, f"Fire Alarm value {valid_value} should be valid"
        
        # Invalid values
        for invalid_value in [2, -1, "yes", "no", 0.5]:
            data = base_data.copy()
            data["Fire Alarm"] = invalid_value
            is_valid, errors = validate_sensor_data(data)
            assert is_valid is False, f"Fire Alarm value {invalid_value} should be invalid"


class TestSensorDataSanitization:
    """Test cases for sensor data sanitization functions."""
    
    def test_sanitize_sensor_data_complete(self):
        """Test sanitization with complete valid data."""
        valid_data = {
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
        
        sanitized = sanitize_sensor_data(valid_data)
        
        # Should preserve all valid values
        for key, value in valid_data.items():
            assert sanitized[key] == value
    
    def test_sanitize_sensor_data_missing_fields(self):
        """Test sanitization fills missing fields with defaults."""
        incomplete_data = {
            "Temperature[C]": 25.5,
            "Humidity[%]": 45.2
        }
        
        sanitized = sanitize_sensor_data(incomplete_data)
        
        # Should have all required fields
        for field in DEFAULT_SENSOR_VALUES.keys():
            assert field in sanitized
        
        # Should preserve provided values
        assert sanitized["Temperature[C]"] == 25.5
        assert sanitized["Humidity[%]"] == 45.2
        
        # Should use defaults for missing values
        assert sanitized["TVOC[ppb]"] == DEFAULT_SENSOR_VALUES["TVOC[ppb]"]
    
    def test_sanitize_sensor_data_outliers(self):
        """Test sanitization handles extreme outliers."""
        outlier_data = {
            "Temperature[C]": 200.0,  # Extreme outlier
            "Humidity[%]": -50.0,     # Extreme outlier
            "Pressure[hPa]": 2000.0,  # Extreme outlier
            "TVOC[ppb]": 150.0,       # Valid
            "eCO2[ppm]": 450.0,
            "Raw H2": 12500,
            "Raw Ethanol": 18500,
            "PM1.0": 5.2,
            "PM2.5": 8.1,
            "NC0.5": 1200,
            "NC1.0": 800,
            "NC2.5": 150,
            "CNT": 50,
            "Fire Alarm": 0
        }
        
        sanitized = sanitize_sensor_data(outlier_data)
        
        # Outliers should be replaced with defaults
        assert sanitized["Temperature[C]"] == DEFAULT_SENSOR_VALUES["Temperature[C]"]
        assert sanitized["Humidity[%]"] == DEFAULT_SENSOR_VALUES["Humidity[%]"]
        assert sanitized["Pressure[hPa]"] == DEFAULT_SENSOR_VALUES["Pressure[hPa]"]
        
        # Valid values should be preserved
        assert sanitized["TVOC[ppb]"] == 150.0
    
    def test_sanitize_sensor_data_type_conversion(self):
        """Test sanitization handles type conversion."""
        string_data = {
            "Temperature[C]": "25.5",
            "Humidity[%]": "45.2",
            "CNT": "50",
            "Fire Alarm": "1"
        }
        
        sanitized = sanitize_sensor_data(string_data)
        
        # Should convert to appropriate types
        assert isinstance(sanitized["Temperature[C]"], float)
        assert isinstance(sanitized["Humidity[%]"], float)
        assert isinstance(sanitized["CNT"], int)
        assert isinstance(sanitized["Fire Alarm"], int)
        
        # Values should be correct
        assert sanitized["Temperature[C]"] == 25.5
        assert sanitized["CNT"] == 50
    
    def test_sanitize_sensor_data_invalid_types(self):
        """Test sanitization handles invalid type conversion."""
        invalid_data = {
            "Temperature[C]": "not_a_number",
            "Humidity[%]": None,
            "CNT": "invalid_int"
        }
        
        sanitized = sanitize_sensor_data(invalid_data)
        
        # Should use defaults for invalid conversions
        assert sanitized["Temperature[C]"] == DEFAULT_SENSOR_VALUES["Temperature[C]"]
        assert sanitized["Humidity[%]"] == DEFAULT_SENSOR_VALUES["Humidity[%]"]
        assert sanitized["CNT"] == DEFAULT_SENSOR_VALUES["CNT"]


class TestRetryDecorator:
    """Test cases for retry decorator functionality."""
    
    def test_retry_decorator_success_first_try(self):
        """Test retry decorator when function succeeds on first try."""
        mock_function = Mock(return_value="success")
        
        @retry_on_kafka_error(max_retries=3, base_delay=0.1)
        def test_function():
            return mock_function()
        
        result = test_function()
        
        assert result == "success"
        assert mock_function.call_count == 1
    
    def test_retry_decorator_kafka_error_retry(self):
        """Test retry decorator with Kafka errors."""
        mock_function = Mock()
        mock_function.side_effect = [
            NoBrokersAvailable(),
            NoBrokersAvailable(),
            "success"
        ]
        
        @retry_on_kafka_error(max_retries=3, base_delay=0.01)
        def test_function():
            return mock_function()
        
        result = test_function()
        
        assert result == "success"
        assert mock_function.call_count == 3
    
    def test_retry_decorator_max_retries_exceeded(self):
        """Test retry decorator when max retries exceeded."""
        mock_function = Mock(side_effect=NoBrokersAvailable())
        
        @retry_on_kafka_error(max_retries=2, base_delay=0.01)
        def test_function():
            return mock_function()
        
        with pytest.raises(KafkaConnectionError):
            test_function()
        
        assert mock_function.call_count == 2
    
    def test_retry_decorator_other_kafka_error(self):
        """Test retry decorator with other Kafka errors."""
        mock_function = Mock(side_effect=KafkaError("Connection failed"))
        
        @retry_on_kafka_error(max_retries=2, base_delay=0.01)
        def test_function():
            return mock_function()
        
        with pytest.raises(KafkaConnectionError):
            test_function()
        
        assert mock_function.call_count == 1  # Should not retry on general KafkaError
    
    def test_retry_decorator_general_exception(self):
        """Test retry decorator with general exceptions."""
        mock_function = Mock(side_effect=ValueError("Invalid data"))
        
        @retry_on_kafka_error(max_retries=2, base_delay=0.01)
        def test_function():
            return mock_function()
        
        with pytest.raises(StreamProcessingError):
            test_function()
        
        assert mock_function.call_count == 1  # Should not retry on general exceptions


class TestErrorHandling:
    """Test cases for error handling functions."""
    
    def test_handle_processing_error_kafka_no_brokers(self):
        """Test error handling for Kafka broker unavailable."""
        error = NoBrokersAvailable()
        
        with pytest.raises(KafkaConnectionError) as exc_info:
            handle_processing_error(error, "test_context")
        
        assert "test_context" in str(exc_info.value)
        assert exc_info.value.context == "test_context"
    
    def test_handle_processing_error_kafka_general(self):
        """Test error handling for general Kafka errors."""
        error = KafkaError("Connection timeout")
        
        with pytest.raises(KafkaConnectionError) as exc_info:
            handle_processing_error(error, "kafka_operation")
        
        assert "kafka_operation" in str(exc_info.value)
    
    def test_handle_processing_error_validation(self):
        """Test error handling for validation errors."""
        error = ValueError("Invalid sensor value")
        
        with pytest.raises(DataValidationError) as exc_info:
            handle_processing_error(error, "validation")
        
        assert "validation" in str(exc_info.value)
    
    def test_handle_processing_error_general(self):
        """Test error handling for general exceptions."""
        error = RuntimeError("Unexpected error")
        
        with pytest.raises(StreamProcessingError) as exc_info:
            handle_processing_error(error, "processing")
        
        assert "processing" in str(exc_info.value)


class TestProcessingMetrics:
    """Test cases for processing metrics functionality."""
    
    def test_processing_metrics_calculation(self):
        """Test processing metrics calculation."""
        start_time = time.time() - 10.0  # 10 seconds ago
        
        metrics = ProcessingMetrics.calculate(
            processed_count=95,
            error_count=5,
            start_time=start_time
        )
        
        assert metrics.processed_count == 95
        assert metrics.error_count == 5
        assert metrics.success_rate == 95.0
        assert metrics.duration >= 9.9  # Should be around 10 seconds
        assert metrics.throughput >= 9.9  # Should be around 10 msg/sec
    
    def test_processing_metrics_zero_messages(self):
        """Test processing metrics with zero messages."""
        start_time = time.time()
        
        metrics = ProcessingMetrics.calculate(
            processed_count=0,
            error_count=0,
            start_time=start_time
        )
        
        assert metrics.success_rate == 0.0
        assert metrics.throughput == 0.0
    
    @patch('data_processing.stream_processing.error_handler.logger')
    def test_log_processing_metrics_normal(self, mock_logger):
        """Test logging of normal processing metrics."""
        start_time = time.time() - 5.0
        
        metrics = log_processing_metrics(100, 5, start_time)
        
        assert metrics.processed_count == 100
        assert metrics.error_count == 5
        mock_logger.info.assert_called()
        
        # Check that info log was called with metrics
        log_call = mock_logger.info.call_args[0][0]
        assert "Processing Metrics" in log_call
        assert "Success Rate: 95.24%" in log_call
    
    @patch('data_processing.stream_processing.error_handler.logger')
    def test_log_processing_metrics_warnings(self, mock_logger):
        """Test logging warnings for poor performance."""
        start_time = time.time() - 100.0  # Long duration for low throughput
        
        metrics = log_processing_metrics(50, 50, start_time)  # 50% success rate
        
        # Should log warnings for low success rate and throughput
        mock_logger.warning.assert_called()
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        
        assert any("Low success rate" in call for call in warning_calls)
        assert any("Low throughput" in call for call in warning_calls)


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_safe_float_conversion_valid(self):
        """Test safe float conversion with valid values."""
        assert safe_float_conversion("25.5", "temperature") == 25.5
        assert safe_float_conversion(30, "humidity") == 30.0
        assert safe_float_conversion(25.5, "pressure") == 25.5
    
    def test_safe_float_conversion_invalid(self):
        """Test safe float conversion with invalid values."""
        assert safe_float_conversion("invalid", "temperature", 20.0) == 20.0
        assert safe_float_conversion(None, "humidity", 50.0) == 50.0
        assert safe_float_conversion("", "pressure", 1013.25) == 1013.25
    
    def test_safe_int_conversion_valid(self):
        """Test safe int conversion with valid values."""
        assert safe_int_conversion("50", "count") == 50
        assert safe_int_conversion(25.7, "alarm") == 25
        assert safe_int_conversion("1", "fire_alarm") == 1
    
    def test_safe_int_conversion_invalid(self):
        """Test safe int conversion with invalid values."""
        assert safe_int_conversion("invalid", "count", 0) == 0
        assert safe_int_conversion(None, "alarm", 1) == 1
        assert safe_int_conversion("", "fire_alarm", 0) == 0


if __name__ == "__main__":
    pytest.main([__file__])
