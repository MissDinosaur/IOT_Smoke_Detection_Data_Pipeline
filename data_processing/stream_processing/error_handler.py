"""
Error handling utilities for stream processing components.

This module provides comprehensive error handling, validation, and retry mechanisms
for robust stream processing operations. It includes:

- Retry decorators for Kafka operations with exponential backoff
- Data validation functions for sensor readings with range checking
- Custom exception classes for different error types
- Centralized error handling and logging with context
- Performance metrics logging for monitoring

Classes:
    StreamProcessingError: Base exception for stream processing errors
    DataValidationError: Exception for data validation failures
    KafkaConnectionError: Exception for Kafka connection issues
    SensorRanges: Configuration class for sensor value ranges
    RetryConfig: Configuration class for retry mechanisms

Functions:
    retry_on_kafka_error: Decorator for automatic retry on Kafka errors
    validate_sensor_data: Validates sensor data structure and ranges
    sanitize_sensor_data: Cleans and normalizes sensor data
    handle_processing_error: Central error handler with classification
    log_processing_metrics: Logs performance metrics for monitoring

Constants:
    DEFAULT_SENSOR_VALUES: Default values for missing sensor readings
    REQUIRED_SENSOR_FIELDS: List of required sensor fields
    NUMERIC_SENSOR_FIELDS: List of numeric sensor fields
"""

import logging
import time
from functools import wraps
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from kafka.errors import KafkaError, NoBrokersAvailable

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry mechanisms."""

    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


@dataclass(frozen=True)
class SensorRanges:
    """Valid ranges for sensor measurements."""

    temperature_min: float = -50.0
    temperature_max: float = 100.0
    humidity_min: float = 0.0
    humidity_max: float = 100.0
    pressure_min: float = 800.0
    pressure_max: float = 1200.0
    tvoc_min: float = 0.0
    eco2_min: float = 0.0
    pm_min: float = 0.0


# Global configuration instances
RETRY_CONFIG = RetryConfig()
SENSOR_RANGES = SensorRanges()

# Default sensor values for missing readings
DEFAULT_SENSOR_VALUES = {
    "Temperature[C]": 20.0,
    "Humidity[%]": 50.0,
    "TVOC[ppb]": 0.0,
    "eCO2[ppm]": 400.0,
    "Raw H2": 0.0,
    "Raw Ethanol": 0.0,
    "Pressure[hPa]": 1013.25,
    "PM1.0": 0.0,
    "PM2.5": 0.0,
    "NC0.5": 0.0,
    "NC1.0": 0.0,
    "NC2.5": 0.0,
    "CNT": 0,
    "Fire Alarm": 0,
}

# Required sensor fields for validation
REQUIRED_SENSOR_FIELDS = [
    "Temperature[C]",
    "Humidity[%]",
    "TVOC[ppb]",
    "eCO2[ppm]",
    "Raw H2",
    "Raw Ethanol",
    "Pressure[hPa]",
    "PM1.0",
    "PM2.5",
    "NC0.5",
    "NC1.0",
    "NC2.5",
    "CNT",
    "Fire Alarm",
]

# Numeric sensor fields for type validation
NUMERIC_SENSOR_FIELDS = [
    "Temperature[C]",
    "Humidity[%]",
    "TVOC[ppb]",
    "eCO2[ppm]",
    "Raw H2",
    "Raw Ethanol",
    "Pressure[hPa]",
    "PM1.0",
    "PM2.5",
    "NC0.5",
    "NC1.0",
    "NC2.5",
    "CNT",
]


# Custom Exception Classes
class StreamProcessingError(Exception):
    """Base exception for stream processing errors."""

    def __init__(self, message: str, context: Optional[str] = None):
        self.context = context
        super().__init__(message)


class DataValidationError(StreamProcessingError):
    """Exception raised for data validation errors."""

    pass


class KafkaConnectionError(StreamProcessingError):
    """Exception raised for Kafka connection issues."""

    pass


def retry_on_kafka_error(
    max_retries: int = RETRY_CONFIG.max_retries,
    base_delay: float = RETRY_CONFIG.base_delay,
    max_delay: float = RETRY_CONFIG.max_delay,
    exponential_base: float = RETRY_CONFIG.exponential_base,
):
    """
    Decorator to retry operations on Kafka errors with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_kafka_error(max_retries=3, base_delay=1.0)
        def connect_to_kafka():
            # Kafka connection code here
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except NoBrokersAvailable:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(
                            f"Failed to connect to Kafka after {max_retries} attempts"
                        )
                        raise KafkaConnectionError(
                            f"Kafka brokers unavailable after {max_retries} retries",
                            context=func.__name__,
                        )

                    # Calculate exponential backoff delay
                    delay = min(
                        base_delay * (exponential_base ** (retries - 1)), max_delay
                    )
                    logger.warning(
                        f"Kafka brokers not available. Retry {retries}/{max_retries} "
                        f"in {delay:.1f}s (function: {func.__name__})"
                    )
                    time.sleep(delay)

                except KafkaError as kafka_error:
                    logger.error(f"Kafka error in {func.__name__}: {str(kafka_error)}")
                    raise KafkaConnectionError(
                        f"Kafka error: {str(kafka_error)}", context=func.__name__
                    ) from kafka_error

                except Exception as general_error:
                    logger.error(
                        f"Unexpected error in {func.__name__}: {str(general_error)}"
                    )
                    raise StreamProcessingError(
                        f"Unexpected error: {str(general_error)}", context=func.__name__
                    ) from general_error

            return wrapper

        return decorator

    return decorator


def validate_sensor_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate sensor data structure and values with comprehensive range checking.

    This function performs thorough validation of IoT sensor data including:
    - Required field presence checking
    - Data type validation for numeric fields
    - Range validation based on sensor specifications
    - Special validation for categorical fields

    Args:
        data: Dictionary containing sensor readings with field names as keys

    Returns:
        Tuple containing:
            - bool: True if all validations pass, False otherwise
            - List[str]: List of validation error messages (empty if valid)

    Example:
        sensor_data = {"Temperature[C]": 25.5, "Humidity[%]": 60.0}
        is_valid, errors = validate_sensor_data(sensor_data)
        if not is_valid:
            print(f"Validation errors: {errors}")
    """
    errors = []

    # Check for missing required fields
    missing_fields = [field for field in REQUIRED_SENSOR_FIELDS if field not in data]
    if missing_fields:
        errors.append(f"Missing required fields: {missing_fields}")

    # Validate numeric fields with range checking
    for field in NUMERIC_SENSOR_FIELDS:
        if field in data and data[field] is not None:
            try:
                value = float(data[field])

                # Apply range validation based on sensor type
                validation_error = _validate_sensor_range(field, value)
                if validation_error:
                    errors.append(validation_error)

            except (ValueError, TypeError):
                errors.append(f"Invalid numeric value for {field}: {data[field]}")

    # Validate Fire Alarm field (categorical)
    if "Fire Alarm" in data:
        if data["Fire Alarm"] not in [0, 1, "0", "1"]:
            errors.append(
                f"Invalid Fire Alarm value: {data['Fire Alarm']} (must be 0 or 1)"
            )

    return len(errors) == 0, errors


def _validate_sensor_range(field: str, value: float) -> Optional[str]:
    """
    Validate sensor value against expected ranges.

    Args:
        field: Sensor field name
        value: Sensor value to validate

    Returns:
        Error message if validation fails, None if valid
    """
    # Temperature validation
    if field == "Temperature[C]":
        if not (
            SENSOR_RANGES.temperature_min <= value <= SENSOR_RANGES.temperature_max
        ):
            return f"Temperature out of range: {value}°C (valid: {SENSOR_RANGES.temperature_min}-{SENSOR_RANGES.temperature_max}°C)"

    # Humidity validation
    elif field == "Humidity[%]":
        if not (SENSOR_RANGES.humidity_min <= value <= SENSOR_RANGES.humidity_max):
            return f"Humidity out of range: {value}% (valid: {SENSOR_RANGES.humidity_min}-{SENSOR_RANGES.humidity_max}%)"

    # Pressure validation
    elif field == "Pressure[hPa]":
        if not (SENSOR_RANGES.pressure_min <= value <= SENSOR_RANGES.pressure_max):
            return f"Pressure out of range: {value} hPa (valid: {SENSOR_RANGES.pressure_min}-{SENSOR_RANGES.pressure_max} hPa)"

    # Air quality sensors (non-negative values)
    elif field in ["TVOC[ppb]", "eCO2[ppm]"]:
        if value < SENSOR_RANGES.tvoc_min:
            return f"Negative value for {field}: {value} (must be >= {SENSOR_RANGES.tvoc_min})"

    # Particulate matter sensors (non-negative values)
    elif field.startswith("PM"):
        if value < SENSOR_RANGES.pm_min:
            return f"Negative particulate matter value for {field}: {value} (must be >= {SENSOR_RANGES.pm_min})"

    # Particle count sensors (non-negative values)
    elif field.startswith("NC"):
        if value < 0:
            return f"Negative particle count for {field}: {value} (must be >= 0)"

    # Gas sensors and other numeric fields (non-negative values)
    elif field in ["Raw H2", "Raw Ethanol", "CNT"]:
        if value < 0:
            return f"Negative value for {field}: {value} (must be >= 0)"

    return None


def sanitize_sensor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensor data by handling missing values and outliers.

    This function cleans raw sensor data by:
    - Filling missing values with sensible defaults
    - Converting data types to appropriate formats
    - Handling extreme outliers by replacing with defaults
    - Ensuring data consistency for downstream processing

    Args:
        data: Raw sensor data dictionary with field names as keys

    Returns:
        Sanitized data dictionary with all required fields and valid values

    Example:
        raw_data = {"Temperature[C]": "25.5", "Humidity[%]": None}
        clean_data = sanitize_sensor_data(raw_data)
        # Result: {"Temperature[C]": 25.5, "Humidity[%]": 50.0, ...}
    """
    sanitized = data.copy()

    for field, default_value in DEFAULT_SENSOR_VALUES.items():
        if field not in sanitized or sanitized[field] is None:
            sanitized[field] = default_value
            logger.debug(f"Set default value for {field}: {default_value}")
        else:
            try:
                # Convert to appropriate type
                if field in ["Fire Alarm", "CNT"]:
                    sanitized[field] = int(float(sanitized[field]))
                else:
                    sanitized[field] = float(sanitized[field])

                # Handle extreme outliers using sensor ranges
                outlier_replacement = _check_and_replace_outliers(
                    field, sanitized[field], default_value
                )
                if outlier_replacement is not None:
                    sanitized[field] = outlier_replacement

            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid value for {field}: {sanitized[field]}, using default"
                )
                sanitized[field] = default_value

    return sanitized


def _check_and_replace_outliers(
    field: str, value: float, default_value: Union[float, int]
) -> Optional[Union[float, int]]:
    """
    Check for extreme outliers and return replacement value if needed.

    Args:
        field: Sensor field name
        value: Current sensor value
        default_value: Default value to use as replacement

    Returns:
        Replacement value if outlier detected, None if value is acceptable
    """
    # Temperature outlier check
    if field == "Temperature[C]":
        if (
            value < SENSOR_RANGES.temperature_min
            or value > SENSOR_RANGES.temperature_max
        ):
            logger.warning(
                f"Temperature outlier detected: {value}°C, using default {default_value}°C"
            )
            return default_value

    # Humidity outlier check
    elif field == "Humidity[%]":
        if value < SENSOR_RANGES.humidity_min or value > SENSOR_RANGES.humidity_max:
            logger.warning(
                f"Humidity outlier detected: {value}%, using default {default_value}%"
            )
            return default_value

    # Pressure outlier check
    elif field == "Pressure[hPa]":
        if value < SENSOR_RANGES.pressure_min or value > SENSOR_RANGES.pressure_max:
            logger.warning(
                f"Pressure outlier detected: {value} hPa, using default {default_value} hPa"
            )
            return default_value

    return None


def handle_processing_error(error: Exception, context: str = "") -> None:
    """
    Central error handler for stream processing with intelligent error classification.

    This function provides centralized error handling by:
    - Classifying errors into appropriate custom exception types
    - Adding contextual information for debugging
    - Logging errors with appropriate severity levels
    - Maintaining error chain for debugging

    Args:
        error: The exception that occurred during processing
        context: Additional context about where the error occurred (e.g., function name)

    Raises:
        KafkaConnectionError: For Kafka-related connection issues
        DataValidationError: For data validation and type conversion errors
        StreamProcessingError: For general stream processing errors

    Example:
        try:
            # Some processing code
            pass
        except Exception as e:
            handle_processing_error(e, context="data_validation")
    """
    error_msg = (
        f"Error in {context}: {str(error)}" if context else f"Error: {str(error)}"
    )

    if isinstance(error, NoBrokersAvailable):
        logger.error(f"Kafka connection failed: {error_msg}")
        raise KafkaConnectionError(error_msg, context=context) from error
    elif isinstance(error, KafkaError):
        logger.error(f"Kafka error: {error_msg}")
        raise KafkaConnectionError(error_msg, context=context) from error
    elif isinstance(error, (ValueError, TypeError)):
        logger.error(f"Data validation error: {error_msg}")
        raise DataValidationError(error_msg, context=context) from error
    else:
        logger.error(f"Unexpected error: {error_msg}")
        raise StreamProcessingError(error_msg, context=context) from error


@dataclass
class ProcessingMetrics:
    """Data class for processing metrics."""

    processed_count: int
    error_count: int
    start_time: float
    duration: float
    success_rate: float
    throughput: float

    @classmethod
    def calculate(
        cls, processed_count: int, error_count: int, start_time: float
    ) -> "ProcessingMetrics":
        """Calculate metrics from raw counts and timing."""
        duration = time.time() - start_time
        total_messages = processed_count + error_count
        success_rate = (
            (processed_count / total_messages * 100) if total_messages > 0 else 0.0
        )
        throughput = (total_messages / duration) if duration > 0 else 0.0

        return cls(
            processed_count=processed_count,
            error_count=error_count,
            start_time=start_time,
            duration=duration,
            success_rate=success_rate,
            throughput=throughput,
        )


def log_processing_metrics(
    processed_count: int, error_count: int, start_time: float
) -> ProcessingMetrics:
    """
    Log processing metrics for monitoring and performance analysis.

    This function calculates and logs comprehensive processing metrics including:
    - Success and error rates
    - Processing throughput (messages per second)
    - Total processing duration
    - Performance indicators for monitoring

    Args:
        processed_count: Number of successfully processed messages
        error_count: Number of messages that failed processing
        start_time: Processing start time (from time.time())

    Returns:
        ProcessingMetrics object with calculated metrics

    Example:
        start = time.time()
        # ... processing logic ...
        metrics = log_processing_metrics(100, 5, start)
        print(f"Success rate: {metrics.success_rate:.2f}%")
    """
    metrics = ProcessingMetrics.calculate(processed_count, error_count, start_time)

    if metrics.processed_count + metrics.error_count > 0:
        logger.info(
            f"Processing Metrics - "
            f"Total: {metrics.processed_count + metrics.error_count}, "
            f"Success: {metrics.processed_count}, "
            f"Errors: {metrics.error_count}, "
            f"Success Rate: {metrics.success_rate:.2f}%, "
            f"Throughput: {metrics.throughput:.2f} msg/sec, "
            f"Duration: {metrics.duration:.2f}s"
        )

        # Log warnings for performance issues
        if metrics.success_rate < 95.0:
            logger.warning(f"Low success rate detected: {metrics.success_rate:.2f}%")
        if metrics.throughput < 1.0:
            logger.warning(f"Low throughput detected: {metrics.throughput:.2f} msg/sec")
    else:
        logger.info("No messages processed in this interval")

    return metrics


# Utility functions for common error handling patterns
def safe_float_conversion(value: Any, field_name: str, default: float = 0.0) -> float:
    """Safely convert value to float with error handling."""
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(
            f"Failed to convert {field_name} to float: {value}, using default {default}"
        )
        return default


def safe_int_conversion(value: Any, field_name: str, default: int = 0) -> int:
    """Safely convert value to int with error handling."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        logger.warning(
            f"Failed to convert {field_name} to int: {value}, using default {default}"
        )
        return default
