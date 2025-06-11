"""
Real-time metrics computation for IoT smoke detection stream processing.
Provides rolling metrics, performance monitoring, and health checks.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[3]
sys.path.append(str(project_root))

import time
import logging
from collections import deque, defaultdict
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("metrics_streaming")


@dataclass
class StreamMetrics:
    """Data class for streaming metrics"""

    timestamp: datetime
    messages_processed: int
    messages_failed: int
    processing_rate: float  # messages per second
    average_processing_time: float  # milliseconds
    anomalies_detected: int
    alerts_triggered: int
    data_quality_score: float  # 0-1 scale
    uptime_seconds: float


class RollingMetricsCalculator:
    """Calculate rolling metrics over time windows"""

    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.window_size = window_minutes * 60  # Convert to seconds
        self.metrics_history = deque()
        self.start_time = time.time()

    def add_metric(self, metric: StreamMetrics):
        """Add a new metric point"""
        self.metrics_history.append(metric)

        # Remove old metrics outside the window
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        while self.metrics_history and self.metrics_history[0].timestamp < cutoff_time:
            self.metrics_history.popleft()

    def get_rolling_average_rate(self) -> float:
        """Get average processing rate over the window"""
        if not self.metrics_history:
            return 0.0

        total_rate = sum(m.processing_rate for m in self.metrics_history)
        return total_rate / len(self.metrics_history)

    def get_rolling_error_rate(self) -> float:
        """Get error rate over the window"""
        if not self.metrics_history:
            return 0.0

        total_processed = sum(m.messages_processed for m in self.metrics_history)
        total_failed = sum(m.messages_failed for m in self.metrics_history)

        if total_processed + total_failed == 0:
            return 0.0

        return total_failed / (total_processed + total_failed)

    def get_rolling_anomaly_rate(self) -> float:
        """Get anomaly detection rate over the window"""
        if not self.metrics_history:
            return 0.0

        total_processed = sum(m.messages_processed for m in self.metrics_history)
        total_anomalies = sum(m.anomalies_detected for m in self.metrics_history)

        if total_processed == 0:
            return 0.0

        return total_anomalies / total_processed

    def get_average_quality_score(self) -> float:
        """Get average data quality score over the window"""
        if not self.metrics_history:
            return 0.0

        total_score = sum(m.data_quality_score for m in self.metrics_history)
        return total_score / len(self.metrics_history)


class StreamingMetricsCollector:
    """Collects and manages streaming metrics"""

    def __init__(self, window_minutes: int = 5):
        self.rolling_calculator = RollingMetricsCalculator(window_minutes)
        self.current_metrics = {
            "messages_processed": 0,
            "messages_failed": 0,
            "anomalies_detected": 0,
            "alerts_triggered": 0,
            "processing_times": deque(maxlen=1000),  # Keep last 1000 processing times
            "data_quality_scores": deque(maxlen=1000),
        }
        self.start_time = time.time()
        self.last_reset_time = time.time()

    def record_message_processed(
        self, processing_time_ms: float, quality_score: float = 1.0
    ):
        """Record a successfully processed message"""
        self.current_metrics["messages_processed"] += 1
        self.current_metrics["processing_times"].append(processing_time_ms)
        self.current_metrics["data_quality_scores"].append(quality_score)

    def record_message_failed(self):
        """Record a failed message"""
        self.current_metrics["messages_failed"] += 1

    def record_anomaly_detected(self):
        """Record an anomaly detection"""
        self.current_metrics["anomalies_detected"] += 1

    def record_alert_triggered(self):
        """Record an alert being triggered"""
        self.current_metrics["alerts_triggered"] += 1

    def get_current_metrics(self) -> StreamMetrics:
        """Get current metrics snapshot"""
        current_time = time.time()
        time_elapsed = current_time - self.last_reset_time

        # Calculate processing rate
        processing_rate = (
            self.current_metrics["messages_processed"] / time_elapsed
            if time_elapsed > 0
            else 0.0
        )

        # Calculate average processing time
        avg_processing_time = (
            sum(self.current_metrics["processing_times"])
            / len(self.current_metrics["processing_times"])
            if self.current_metrics["processing_times"]
            else 0.0
        )

        # Calculate average data quality score
        avg_quality_score = (
            sum(self.current_metrics["data_quality_scores"])
            / len(self.current_metrics["data_quality_scores"])
            if self.current_metrics["data_quality_scores"]
            else 1.0
        )

        # Calculate uptime
        uptime = current_time - self.start_time

        return StreamMetrics(
            timestamp=datetime.now(),
            messages_processed=self.current_metrics["messages_processed"],
            messages_failed=self.current_metrics["messages_failed"],
            processing_rate=processing_rate,
            average_processing_time=avg_processing_time,
            anomalies_detected=self.current_metrics["anomalies_detected"],
            alerts_triggered=self.current_metrics["alerts_triggered"],
            data_quality_score=avg_quality_score,
            uptime_seconds=uptime,
        )

    def reset_interval_metrics(self):
        """Reset metrics for the next interval"""
        self.current_metrics["messages_processed"] = 0
        self.current_metrics["messages_failed"] = 0
        self.current_metrics["anomalies_detected"] = 0
        self.current_metrics["alerts_triggered"] = 0
        self.last_reset_time = time.time()

    def log_metrics_summary(self):
        """Log a summary of current metrics"""
        metrics = self.get_current_metrics()
        self.rolling_calculator.add_metric(metrics)

        # Log current interval metrics
        logger.info(f"Stream Processing Metrics Summary:")
        logger.info(f"  Messages Processed: {metrics.messages_processed}")
        logger.info(f"  Messages Failed: {metrics.messages_failed}")
        logger.info(f"  Processing Rate: {metrics.processing_rate:.2f} msg/sec")
        logger.info(f"  Avg Processing Time: {metrics.average_processing_time:.2f} ms")
        logger.info(f"  Anomalies Detected: {metrics.anomalies_detected}")
        logger.info(f"  Alerts Triggered: {metrics.alerts_triggered}")
        logger.info(f"  Data Quality Score: {metrics.data_quality_score:.3f}")
        logger.info(f"  Uptime: {metrics.uptime_seconds:.0f} seconds")

        # Log rolling metrics
        rolling_rate = self.rolling_calculator.get_rolling_average_rate()
        rolling_error_rate = self.rolling_calculator.get_rolling_error_rate()
        rolling_anomaly_rate = self.rolling_calculator.get_rolling_anomaly_rate()
        rolling_quality = self.rolling_calculator.get_average_quality_score()

        logger.info(f"Rolling Metrics (5-min window):")
        logger.info(f"  Avg Processing Rate: {rolling_rate:.2f} msg/sec")
        logger.info(f"  Error Rate: {rolling_error_rate:.3f}")
        logger.info(f"  Anomaly Rate: {rolling_anomaly_rate:.3f}")
        logger.info(f"  Avg Quality Score: {rolling_quality:.3f}")

        # Check for performance issues
        if rolling_error_rate > 0.05:  # 5% error rate threshold
            logger.warning(f"High error rate detected: {rolling_error_rate:.3f}")

        if rolling_quality < 0.8:  # 80% quality threshold
            logger.warning(f"Low data quality detected: {rolling_quality:.3f}")

        if rolling_rate < 1.0:  # Less than 1 message per second
            logger.warning(f"Low processing rate detected: {rolling_rate:.2f} msg/sec")

    def export_metrics_json(self, filepath: str):
        """Export current metrics to JSON file"""
        metrics = self.get_current_metrics()

        # Convert to dictionary and handle datetime serialization
        metrics_dict = asdict(metrics)
        metrics_dict["timestamp"] = metrics_dict["timestamp"].isoformat()

        # Add rolling metrics
        metrics_dict["rolling_metrics"] = {
            "avg_processing_rate": self.rolling_calculator.get_rolling_average_rate(),
            "error_rate": self.rolling_calculator.get_rolling_error_rate(),
            "anomaly_rate": self.rolling_calculator.get_rolling_anomaly_rate(),
            "avg_quality_score": self.rolling_calculator.get_average_quality_score(),
        }

        try:
            with open(filepath, "w") as f:
                json.dump(metrics_dict, f, indent=2)
            logger.debug(f"Metrics exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")


# Global metrics collector instance
metrics_collector = StreamingMetricsCollector()


def get_metrics_collector() -> StreamingMetricsCollector:
    """Get the global metrics collector instance"""
    return metrics_collector


def start_metrics_logging(interval_seconds: int = 60):
    """Start periodic metrics logging"""
    import threading

    def log_metrics_periodically():
        while True:
            time.sleep(interval_seconds)
            metrics_collector.log_metrics_summary()
            metrics_collector.reset_interval_metrics()

    # Start metrics logging in a separate thread
    metrics_thread = threading.Thread(target=log_metrics_periodically, daemon=True)
    metrics_thread.start()
    logger.info(f"Started metrics logging with {interval_seconds}s interval")


if __name__ == "__main__":
    # Example usage
    collector = get_metrics_collector()

    # Simulate some metrics
    for i in range(100):
        collector.record_message_processed(processing_time_ms=50.0, quality_score=0.95)
        if i % 20 == 0:
            collector.record_anomaly_detected()
        if i % 50 == 0:
            collector.record_alert_triggered()
        time.sleep(0.1)

    # Log summary
    collector.log_metrics_summary()

    # Export to file
    collector.export_metrics_json("stream_metrics.json")
