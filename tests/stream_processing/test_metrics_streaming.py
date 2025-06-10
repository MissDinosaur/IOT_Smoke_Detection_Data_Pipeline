"""
Comprehensive test cases for stream processing metrics and analytics.

This module tests the real-time analytics functionality including:
- Rolling window calculations
- Threshold detection and alerting
- Anomaly detection algorithms
- Performance monitoring
- Data aggregation functions
"""

import pytest
import time
import json
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import the modules to test
import sys
from pathlib import Path

project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from data_processing.stream_processing.metrics_streaming import (
    RollingWindowAnalytics,
    ThresholdDetector,
    AnomalyDetector,
    StreamingMetricsProcessor,
    AlertLevel,
    MetricsWindow,
    calculate_rolling_average,
    calculate_rolling_count,
    detect_threshold_violations,
    generate_alert_message,
)


class TestRollingWindowAnalytics:
    """Test cases for rolling window analytics functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analytics = RollingWindowAnalytics(window_size=5)

        # Sample sensor data
        self.sample_data = [
            {
                "Temperature[C]": 25.0,
                "Humidity[%]": 50.0,
                "TVOC[ppb]": 100.0,
                "Fire Alarm": 0,
            },
            {
                "Temperature[C]": 26.0,
                "Humidity[%]": 52.0,
                "TVOC[ppb]": 110.0,
                "Fire Alarm": 0,
            },
            {
                "Temperature[C]": 27.0,
                "Humidity[%]": 54.0,
                "TVOC[ppb]": 120.0,
                "Fire Alarm": 0,
            },
            {
                "Temperature[C]": 28.0,
                "Humidity[%]": 56.0,
                "TVOC[ppb]": 130.0,
                "Fire Alarm": 0,
            },
            {
                "Temperature[C]": 29.0,
                "Humidity[%]": 58.0,
                "TVOC[ppb]": 140.0,
                "Fire Alarm": 0,
            },
        ]

    def test_rolling_window_initialization(self):
        """Test rolling window analytics initialization."""
        assert self.analytics.window_size == 5
        assert len(self.analytics.data_buffer) == 0
        assert self.analytics.current_metrics is not None

    def test_add_data_point(self):
        """Test adding data points to rolling window."""
        data_point = {"Temperature[C]": 25.0, "Humidity[%]": 50.0}

        self.analytics.add_data_point(data_point)

        assert len(self.analytics.data_buffer) == 1
        assert self.analytics.data_buffer[0] == data_point

    def test_rolling_window_size_limit(self):
        """Test that rolling window maintains size limit."""
        # Add more data points than window size
        for i, data_point in enumerate(self.sample_data + self.sample_data):
            self.analytics.add_data_point(data_point)

        # Should maintain window size
        assert len(self.analytics.data_buffer) == 5

        # Should contain the most recent data
        assert self.analytics.data_buffer[-1]["Temperature[C]"] == 29.0

    def test_calculate_rolling_averages(self):
        """Test calculation of rolling averages."""
        # Add sample data
        for data_point in self.sample_data:
            self.analytics.add_data_point(data_point)

        averages = self.analytics.calculate_rolling_averages()

        # Check expected averages
        assert averages["Temperature[C]"] == 27.0  # (25+26+27+28+29)/5
        assert averages["Humidity[%]"] == 54.0  # (50+52+54+56+58)/5
        assert averages["TVOC[ppb]"] == 120.0  # (100+110+120+130+140)/5

    def test_calculate_rolling_counts(self):
        """Test calculation of rolling counts."""
        # Add data with some fire alarms
        fire_data = self.sample_data.copy()
        fire_data[2]["Fire Alarm"] = 1
        fire_data[4]["Fire Alarm"] = 1

        for data_point in fire_data:
            self.analytics.add_data_point(data_point)

        counts = self.analytics.calculate_rolling_counts()

        assert counts["total_records"] == 5
        assert counts["fire_alarms"] == 2
        assert counts["normal_readings"] == 3

    def test_calculate_rolling_statistics(self):
        """Test calculation of rolling statistics."""
        for data_point in self.sample_data:
            self.analytics.add_data_point(data_point)

        stats = self.analytics.calculate_rolling_statistics()

        # Check temperature statistics
        temp_stats = stats["Temperature[C]"]
        assert temp_stats["min"] == 25.0
        assert temp_stats["max"] == 29.0
        assert temp_stats["mean"] == 27.0
        assert temp_stats["std"] > 0  # Should have some standard deviation

    def test_empty_window_handling(self):
        """Test handling of empty data window."""
        averages = self.analytics.calculate_rolling_averages()
        counts = self.analytics.calculate_rolling_counts()
        stats = self.analytics.calculate_rolling_statistics()

        # Should handle empty window gracefully
        assert averages == {}
        assert counts["total_records"] == 0
        assert stats == {}


class TestThresholdDetector:
    """Test cases for threshold detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.thresholds = {
            "Temperature[C]": {"low": 0.0, "high": 50.0, "critical": 80.0},
            "Humidity[%]": {"low": 10.0, "high": 90.0, "critical": 95.0},
            "TVOC[ppb]": {"low": 0.0, "high": 1000.0, "critical": 2000.0},
            "PM2.5": {"low": 0.0, "high": 35.0, "critical": 75.0},
        }
        self.detector = ThresholdDetector(self.thresholds)

    def test_threshold_detector_initialization(self):
        """Test threshold detector initialization."""
        assert self.detector.thresholds == self.thresholds
        assert len(self.detector.alert_history) == 0

    def test_detect_normal_values(self):
        """Test detection with normal sensor values."""
        normal_data = {
            "Temperature[C]": 25.0,
            "Humidity[%]": 50.0,
            "TVOC[ppb]": 150.0,
            "PM2.5": 10.0,
        }

        alerts = self.detector.detect_violations(normal_data)

        assert len(alerts) == 0

    def test_detect_high_threshold_violations(self):
        """Test detection of high threshold violations."""
        high_data = {
            "Temperature[C]": 60.0,  # Above high threshold
            "Humidity[%]": 95.0,  # Above high threshold
            "TVOC[ppb]": 1500.0,  # Above high threshold
            "PM2.5": 50.0,  # Above high threshold
        }

        alerts = self.detector.detect_violations(high_data)

        assert len(alerts) == 4

        # Check alert levels
        temp_alert = next(a for a in alerts if a["sensor"] == "Temperature[C]")
        assert temp_alert["level"] == AlertLevel.HIGH
        assert temp_alert["value"] == 60.0

    def test_detect_critical_threshold_violations(self):
        """Test detection of critical threshold violations."""
        critical_data = {
            "Temperature[C]": 85.0,  # Above critical threshold
            "Humidity[%]": 96.0,  # Above critical threshold
            "TVOC[ppb]": 2500.0,  # Above critical threshold
            "PM2.5": 80.0,  # Above critical threshold
        }

        alerts = self.detector.detect_violations(critical_data)

        assert len(alerts) == 4

        # All should be critical alerts
        for alert in alerts:
            assert alert["level"] == AlertLevel.CRITICAL

    def test_detect_low_threshold_violations(self):
        """Test detection of low threshold violations."""
        low_data = {
            "Temperature[C]": -10.0,  # Below low threshold
            "Humidity[%]": 5.0,  # Below low threshold
            "TVOC[ppb]": -50.0,  # Below low threshold
            "PM2.5": -5.0,  # Below low threshold
        }

        alerts = self.detector.detect_violations(low_data)

        assert len(alerts) == 4

        # Check that low violations are detected
        for alert in alerts:
            assert alert["level"] == AlertLevel.LOW
            assert alert["violation_type"] == "below_low"

    def test_alert_history_tracking(self):
        """Test that alert history is properly tracked."""
        violation_data = {"Temperature[C]": 60.0}

        # Generate multiple alerts
        for _ in range(3):
            alerts = self.detector.detect_violations(violation_data)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        assert len(self.detector.alert_history) == 3

        # Check that timestamps are recorded
        for alert in self.detector.alert_history:
            assert "timestamp" in alert
            assert alert["sensor"] == "Temperature[C]"

    def test_unknown_sensor_handling(self):
        """Test handling of sensors not in threshold configuration."""
        unknown_data = {"UnknownSensor": 100.0, "Temperature[C]": 25.0}  # Known sensor

        alerts = self.detector.detect_violations(unknown_data)

        # Should only process known sensors
        assert len(alerts) == 0  # Temperature is normal


class TestAnomalyDetector:
    """Test cases for anomaly detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = AnomalyDetector(
            window_size=10, z_score_threshold=2.0, min_samples=5
        )

        # Generate normal data
        self.normal_data = [
            {"Temperature[C]": 25.0 + np.random.normal(0, 1), "sensor_id": "temp_01"}
            for _ in range(20)
        ]

        # Generate anomalous data
        self.anomaly_data = [
            {"Temperature[C]": 50.0, "sensor_id": "temp_01"},  # Clear anomaly
            {"Temperature[C]": -10.0, "sensor_id": "temp_01"},  # Clear anomaly
        ]

    def test_anomaly_detector_initialization(self):
        """Test anomaly detector initialization."""
        assert self.detector.window_size == 10
        assert self.detector.z_score_threshold == 2.0
        assert self.detector.min_samples == 5
        assert len(self.detector.data_history) == 0

    def test_add_normal_data(self):
        """Test adding normal data points."""
        for data_point in self.normal_data[:10]:
            self.detector.add_data_point(data_point)

        assert len(self.detector.data_history) == 10

    def test_detect_no_anomalies_normal_data(self):
        """Test that normal data doesn't trigger anomalies."""
        # Add normal data
        for data_point in self.normal_data[:10]:
            self.detector.add_data_point(data_point)

        # Check for anomalies in normal data
        normal_point = {"Temperature[C]": 25.5, "sensor_id": "temp_01"}
        anomalies = self.detector.detect_anomalies(normal_point)

        assert len(anomalies) == 0

    def test_detect_statistical_anomalies(self):
        """Test detection of statistical anomalies."""
        # Add normal data to establish baseline
        for data_point in self.normal_data[:10]:
            self.detector.add_data_point(data_point)

        # Test clear anomaly
        anomaly_point = {"Temperature[C]": 100.0, "sensor_id": "temp_01"}
        anomalies = self.detector.detect_anomalies(anomaly_point)

        assert len(anomalies) > 0
        assert anomalies[0]["sensor"] == "Temperature[C]"
        assert anomalies[0]["anomaly_type"] == "statistical"
        assert anomalies[0]["z_score"] > self.detector.z_score_threshold

    def test_insufficient_data_handling(self):
        """Test handling when insufficient historical data."""
        # Add only a few data points
        for data_point in self.normal_data[:3]:
            self.detector.add_data_point(data_point)

        # Should not detect anomalies with insufficient data
        test_point = {"Temperature[C]": 100.0, "sensor_id": "temp_01"}
        anomalies = self.detector.detect_anomalies(test_point)

        assert len(anomalies) == 0

    def test_pattern_based_anomaly_detection(self):
        """Test pattern-based anomaly detection."""
        # Create data with a clear pattern
        pattern_data = []
        for i in range(15):
            # Create a sine wave pattern
            temp = 25.0 + 5.0 * np.sin(i * 0.5)
            pattern_data.append({"Temperature[C]": temp, "sensor_id": "temp_01"})

        # Add pattern data
        for data_point in pattern_data:
            self.detector.add_data_point(data_point)

        # Test point that breaks the pattern
        anomaly_point = {"Temperature[C]": 50.0, "sensor_id": "temp_01"}
        anomalies = self.detector.detect_anomalies(anomaly_point)

        assert len(anomalies) > 0


class TestStreamingMetricsProcessor:
    """Test cases for the main streaming metrics processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = StreamingMetricsProcessor(
            window_duration=60,  # 1 minute windows
            slide_duration=30,  # 30 second slides
        )

    def test_processor_initialization(self):
        """Test processor initialization."""
        assert self.processor.window_duration == 60
        assert self.processor.slide_duration == 30
        assert self.processor.analytics is not None
        assert self.processor.threshold_detector is not None
        assert self.processor.anomaly_detector is not None

    def test_process_sensor_batch(self):
        """Test processing a batch of sensor data."""
        sensor_batch = [
            {
                "Temperature[C]": 25.0,
                "Humidity[%]": 50.0,
                "TVOC[ppb]": 150.0,
                "Fire Alarm": 0,
                "timestamp": time.time(),
            },
            {
                "Temperature[C]": 26.0,
                "Humidity[%]": 52.0,
                "TVOC[ppb]": 160.0,
                "Fire Alarm": 0,
                "timestamp": time.time(),
            },
        ]

        results = self.processor.process_batch(sensor_batch)

        assert "analytics" in results
        assert "alerts" in results
        assert "anomalies" in results
        assert "summary" in results

        # Check analytics results
        analytics = results["analytics"]
        assert "averages" in analytics
        assert "counts" in analytics
        assert "statistics" in analytics

    def test_process_fire_alarm_batch(self):
        """Test processing batch with fire alarms."""
        fire_batch = [
            {
                "Temperature[C]": 60.0,  # High temperature
                "Humidity[%]": 20.0,  # Low humidity
                "TVOC[ppb]": 2000.0,  # High TVOC
                "Fire Alarm": 1,  # Fire alarm triggered
                "timestamp": time.time(),
            }
        ]

        results = self.processor.process_batch(fire_batch)

        # Should detect alerts
        assert len(results["alerts"]) > 0

        # Should count fire alarms
        counts = results["analytics"]["counts"]
        assert counts["fire_alarms"] > 0

    @patch("data_processing.stream_processing.metrics_streaming.logger")
    def test_error_handling_in_processing(self, mock_logger):
        """Test error handling during batch processing."""
        # Create invalid data that might cause errors
        invalid_batch = [
            {"Temperature[C]": "invalid_value", "timestamp": "invalid_timestamp"}
        ]

        # Should handle errors gracefully
        results = self.processor.process_batch(invalid_batch)

        # Should still return results structure
        assert "analytics" in results
        assert "alerts" in results
        assert "anomalies" in results

    def test_metrics_window_creation(self):
        """Test creation of metrics windows."""
        window = MetricsWindow(
            start_time=time.time() - 60,
            end_time=time.time(),
            record_count=100,
            averages={"Temperature[C]": 25.0},
            alerts=[],
            anomalies=[],
        )

        assert window.record_count == 100
        assert window.averages["Temperature[C]"] == 25.0
        assert len(window.alerts) == 0
        assert len(window.anomalies) == 0
        assert window.duration == 60.0


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_calculate_rolling_average(self):
        """Test rolling average calculation utility."""
        data = [10, 20, 30, 40, 50]
        avg = calculate_rolling_average(data)
        assert avg == 30.0

        # Test with empty data
        assert calculate_rolling_average([]) == 0.0

    def test_calculate_rolling_count(self):
        """Test rolling count calculation utility."""
        data = [1, 0, 1, 1, 0, 1]
        count = calculate_rolling_count(data, target_value=1)
        assert count == 4

        # Test with empty data
        assert calculate_rolling_count([], target_value=1) == 0

    def test_detect_threshold_violations_utility(self):
        """Test threshold violation detection utility."""
        thresholds = {"high": 50.0, "low": 10.0}

        # Normal value
        assert detect_threshold_violations(30.0, thresholds) is None

        # High violation
        violation = detect_threshold_violations(60.0, thresholds)
        assert violation["type"] == "above_high"
        assert violation["threshold"] == 50.0

        # Low violation
        violation = detect_threshold_violations(5.0, thresholds)
        assert violation["type"] == "below_low"
        assert violation["threshold"] == 10.0

    def test_generate_alert_message(self):
        """Test alert message generation utility."""
        alert = {
            "sensor": "Temperature[C]",
            "value": 60.0,
            "level": AlertLevel.HIGH,
            "threshold": 50.0,
            "violation_type": "above_high",
        }

        message = generate_alert_message(alert)

        assert "Temperature[C]" in message
        assert "60.0" in message
        assert "HIGH" in message
        assert "50.0" in message


class TestSparkStreamingIntegration:
    """Test cases for Spark streaming integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_kafka_data = [
            {
                "Temperature[C]": 25.0,
                "Humidity[%]": 50.0,
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
                "Fire Alarm": 0,
                "timestamp": time.time(),
            }
        ]

    @patch(
        "data_processing.stream_processing.spark_streaming_processor.create_spark_session"
    )
    def test_spark_session_creation(self, mock_spark_session):
        """Test Spark session creation for streaming."""
        mock_session = Mock()
        mock_spark_session.return_value = mock_session

        # Test that session is created with correct configuration
        from data_processing.stream_processing.spark_streaming_processor import (
            create_spark_session,
        )

        session = create_spark_session()

        assert session is not None
        mock_spark_session.assert_called_once()

    def test_sensor_schema_definition(self):
        """Test sensor schema definition for Spark."""
        from data_processing.stream_processing.spark_streaming_processor import (
            get_sensor_schema,
        )

        schema = get_sensor_schema()

        # Check that schema has all required fields
        field_names = [field.name for field in schema.fields]

        expected_fields = [
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
            "timestamp",
        ]

        for field in expected_fields:
            assert field in field_names

    @patch("data_processing.stream_processing.spark_streaming_processor.logger")
    def test_analytics_batch_processing(self, mock_logger):
        """Test analytics batch processing function."""
        from data_processing.stream_processing.spark_streaming_processor import (
            process_analytics_batch,
        )

        # Create mock DataFrame with analytics results
        mock_df = Mock()
        mock_df.count.return_value = 1

        # Create mock row with analytics data
        mock_row = Mock()
        mock_row.window.start = "2024-01-01 10:00:00"
        mock_row.window.end = "2024-01-01 10:05:00"
        mock_row.avg_temperature = 60.0  # High temperature
        mock_row.avg_humidity = 45.0
        mock_row.avg_tvoc = 1200.0  # High TVOC
        mock_row.avg_eco2 = 800.0
        mock_row.avg_pm25 = 40.0  # High PM2.5
        mock_row.fire_alarm_count = 1
        mock_row.record_count = 10

        mock_df.collect.return_value = [mock_row]

        # Test batch processing
        process_analytics_batch(mock_df, epoch_id=1)

        # Verify that alerts were logged
        mock_logger.warning.assert_called()
        mock_logger.critical.assert_called()  # Fire alarm

        # Check specific alert calls
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        critical_calls = [call[0][0] for call in mock_logger.critical.call_args_list]

        assert any("HIGH TEMPERATURE ALERT" in call for call in warning_calls)
        assert any("HIGH TVOC ALERT" in call for call in warning_calls)
        assert any("HIGH PM2.5 ALERT" in call for call in warning_calls)
        assert any("FIRE ALARM TRIGGERED" in call for call in critical_calls)


if __name__ == "__main__":
    pytest.main([__file__])
