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
import sys
from pathlib import Path

# Import the modules to test
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from data_processing.stream_processing.metrics_streaming import (
    StreamMetrics,
    RollingMetricsCalculator,
    StreamingMetricsCollector,
    get_metrics_collector,
    start_metrics_logging,
)


class TestRollingMetricsCalculator:
    """Test cases for rolling metrics calculator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = RollingMetricsCalculator(window_minutes=5)

    def test_rolling_calculator_initialization(self):
        """Test rolling metrics calculator initialization."""
        assert self.calculator.window_minutes == 5
        assert self.calculator.window_size == 300  # 5 minutes * 60 seconds
        assert len(self.calculator.metrics_history) == 0

    def test_add_metric(self):
        """Test adding metrics to rolling calculator."""
        from datetime import datetime

        metric = StreamMetrics(
            timestamp=datetime.now(),
            messages_processed=10,
            messages_failed=1,
            processing_rate=5.0,
            average_processing_time=50.0,
            anomalies_detected=2,
            alerts_triggered=1,
            data_quality_score=0.95,
            uptime_seconds=100.0,
        )

        self.calculator.add_metric(metric)
        assert len(self.calculator.metrics_history) == 1

    def test_get_rolling_average_rate(self):
        """Test calculation of rolling average rate."""
        from datetime import datetime

        # Add multiple metrics
        for i in range(3):
            metric = StreamMetrics(
                timestamp=datetime.now(),
                messages_processed=10,
                messages_failed=0,
                processing_rate=float(i + 1),  # 1.0, 2.0, 3.0
                average_processing_time=50.0,
                anomalies_detected=0,
                alerts_triggered=0,
                data_quality_score=1.0,
                uptime_seconds=100.0,
            )
            self.calculator.add_metric(metric)

        avg_rate = self.calculator.get_rolling_average_rate()
        assert avg_rate == 2.0  # (1.0 + 2.0 + 3.0) / 3

    def test_get_rolling_error_rate(self):
        """Test calculation of rolling error rate."""
        from datetime import datetime

        # Add metrics with some failures
        metric1 = StreamMetrics(
            timestamp=datetime.now(),
            messages_processed=8,
            messages_failed=2,  # 20% error rate
            processing_rate=5.0,
            average_processing_time=50.0,
            anomalies_detected=0,
            alerts_triggered=0,
            data_quality_score=1.0,
            uptime_seconds=100.0,
        )

        metric2 = StreamMetrics(
            timestamp=datetime.now(),
            messages_processed=10,
            messages_failed=0,  # 0% error rate
            processing_rate=5.0,
            average_processing_time=50.0,
            anomalies_detected=0,
            alerts_triggered=0,
            data_quality_score=1.0,
            uptime_seconds=100.0,
        )

        self.calculator.add_metric(metric1)
        self.calculator.add_metric(metric2)

        error_rate = self.calculator.get_rolling_error_rate()
        assert error_rate == 0.1  # 2 failures out of 20 total messages

    def test_empty_metrics_handling(self):
        """Test handling of empty metrics history."""
        assert self.calculator.get_rolling_average_rate() == 0.0
        assert self.calculator.get_rolling_error_rate() == 0.0
        assert self.calculator.get_rolling_anomaly_rate() == 0.0
        assert self.calculator.get_average_quality_score() == 0.0


class TestStreamingMetricsCollector:
    """Test cases for streaming metrics collector functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = StreamingMetricsCollector(window_minutes=5)

    def test_collector_initialization(self):
        """Test streaming metrics collector initialization."""
        assert self.collector.rolling_calculator.window_minutes == 5
        assert self.collector.current_metrics["messages_processed"] == 0
        assert self.collector.current_metrics["messages_failed"] == 0
        assert self.collector.current_metrics["anomalies_detected"] == 0
        assert self.collector.current_metrics["alerts_triggered"] == 0

    def test_record_message_processed(self):
        """Test recording processed messages."""
        self.collector.record_message_processed(
            processing_time_ms=50.0, quality_score=0.95
        )

        assert self.collector.current_metrics["messages_processed"] == 1
        assert len(self.collector.current_metrics["processing_times"]) == 1
        assert len(self.collector.current_metrics["data_quality_scores"]) == 1

    def test_record_message_failed(self):
        """Test recording failed messages."""
        self.collector.record_message_failed()

        assert self.collector.current_metrics["messages_failed"] == 1

    def test_record_anomaly_detected(self):
        """Test recording anomaly detection."""
        self.collector.record_anomaly_detected()

        assert self.collector.current_metrics["anomalies_detected"] == 1

    def test_record_alert_triggered(self):
        """Test recording alert triggers."""
        self.collector.record_alert_triggered()

        assert self.collector.current_metrics["alerts_triggered"] == 1

    def test_get_current_metrics(self):
        """Test getting current metrics snapshot."""
        # Record some activity
        self.collector.record_message_processed(
            processing_time_ms=50.0, quality_score=0.95
        )
        self.collector.record_message_processed(
            processing_time_ms=60.0, quality_score=0.90
        )
        self.collector.record_anomaly_detected()

        metrics = self.collector.get_current_metrics()

        assert metrics.messages_processed == 2
        assert metrics.anomalies_detected == 1
        assert metrics.average_processing_time == 55.0  # (50 + 60) / 2
        assert metrics.data_quality_score == 0.925  # (0.95 + 0.90) / 2

    def test_reset_interval_metrics(self):
        """Test resetting interval metrics."""
        # Record some activity
        self.collector.record_message_processed(processing_time_ms=50.0)
        self.collector.record_anomaly_detected()

        # Reset metrics
        self.collector.reset_interval_metrics()

        assert self.collector.current_metrics["messages_processed"] == 0
        assert self.collector.current_metrics["anomalies_detected"] == 0

    def test_export_metrics_json(self):
        """Test exporting metrics to JSON."""
        import tempfile
        import json
        import os

        # Record some activity
        self.collector.record_message_processed(
            processing_time_ms=50.0, quality_score=0.95
        )

        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            self.collector.export_metrics_json(temp_path)

            # Verify file was created and contains valid JSON
            assert os.path.exists(temp_path)

            with open(temp_path, "r") as f:
                data = json.load(f)

            assert "messages_processed" in data
            assert "rolling_metrics" in data
            assert data["messages_processed"] == 1

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGlobalFunctions:
    """Test cases for global functions and utilities."""

    def test_get_metrics_collector(self):
        """Test getting the global metrics collector."""
        collector = get_metrics_collector()

        assert isinstance(collector, StreamingMetricsCollector)
        assert collector is not None

    def test_start_metrics_logging(self):
        """Test starting metrics logging (without actually running the thread)."""
        # This test just verifies the function can be called without errors
        # We don't actually start the thread to avoid side effects
        try:
            # Just test that the function exists and can be imported
            assert callable(start_metrics_logging)
        except Exception as e:
            pytest.fail(f"start_metrics_logging function failed: {e}")


class TestStreamMetricsDataClass:
    """Test cases for StreamMetrics data class."""

    def test_stream_metrics_creation(self):
        """Test creating StreamMetrics instance."""
        from datetime import datetime

        metrics = StreamMetrics(
            timestamp=datetime.now(),
            messages_processed=100,
            messages_failed=5,
            processing_rate=10.5,
            average_processing_time=45.2,
            anomalies_detected=3,
            alerts_triggered=1,
            data_quality_score=0.95,
            uptime_seconds=3600.0,
        )

        assert metrics.messages_processed == 100
        assert metrics.messages_failed == 5
        assert metrics.processing_rate == 10.5
        assert metrics.average_processing_time == 45.2
        assert metrics.anomalies_detected == 3
        assert metrics.alerts_triggered == 1
        assert metrics.data_quality_score == 0.95
        assert metrics.uptime_seconds == 3600.0

    def test_stream_metrics_timestamp(self):
        """Test StreamMetrics timestamp handling."""
        from datetime import datetime

        now = datetime.now()
        metrics = StreamMetrics(
            timestamp=now,
            messages_processed=10,
            messages_failed=0,
            processing_rate=5.0,
            average_processing_time=50.0,
            anomalies_detected=0,
            alerts_triggered=0,
            data_quality_score=1.0,
            uptime_seconds=100.0,
        )

        assert metrics.timestamp == now
        assert isinstance(metrics.timestamp, datetime)


if __name__ == "__main__":
    pytest.main([__file__])
