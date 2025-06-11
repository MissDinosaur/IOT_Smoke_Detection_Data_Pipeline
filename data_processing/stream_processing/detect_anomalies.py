"""
Advanced anomaly detection for IoT smoke detection data.
Implements multiple detection algorithms including statistical and rule-based approaches.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[3]
sys.path.append(str(project_root))

import logging
import numpy as np
from collections import deque
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("anomaly_detector")


@dataclass
class AnomalyAlert:
    """Data class for anomaly alerts"""

    timestamp: datetime
    sensor: str
    value: float
    threshold: float
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    message: str
    alert_type: str  # 'THRESHOLD', 'STATISTICAL', 'PATTERN'


class RollingStatistics:
    """Maintains rolling statistics for anomaly detection"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.values = deque(maxlen=window_size)

    def add_value(self, value: float):
        """Add a new value to the rolling window"""
        if value is not None and not np.isnan(value):
            self.values.append(value)

    def get_mean(self) -> Optional[float]:
        """Get the rolling mean"""
        if len(self.values) == 0:
            return None
        return np.mean(self.values)

    def get_std(self) -> Optional[float]:
        """Get the rolling standard deviation"""
        if len(self.values) < 2:
            return None
        return np.std(self.values)

    def get_percentile(self, percentile: float) -> Optional[float]:
        """Get the specified percentile"""
        if len(self.values) == 0:
            return None
        return np.percentile(self.values, percentile)


class SmokeAnomalyDetector:
    """Advanced anomaly detector for smoke detection sensors"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.rolling_stats = {}
        self.thresholds = self._get_default_thresholds()
        self.initialize_rolling_stats()

    def initialize_rolling_stats(self):
        """Initialize rolling statistics for all sensors"""
        sensors = [
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
        ]

        for sensor in sensors:
            self.rolling_stats[sensor] = RollingStatistics(self.window_size)

    def _get_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get default threshold values for different sensors"""
        return {
            "Temperature[C]": {
                "low_critical": -20,
                "low_high": 0,
                "high_medium": 40,
                "high_high": 50,
                "high_critical": 70,
            },
            "Humidity[%]": {
                "low_critical": 5,
                "low_high": 15,
                "high_medium": 80,
                "high_high": 90,
                "high_critical": 95,
            },
            "TVOC[ppb]": {
                "low_medium": 0,
                "high_medium": 500,
                "high_high": 1000,
                "high_critical": 2000,
            },
            "eCO2[ppm]": {
                "low_medium": 0,
                "high_medium": 800,
                "high_high": 1000,
                "high_critical": 1500,
            },
            "PM2.5": {
                "low_medium": 0,
                "high_medium": 25,
                "high_high": 35,
                "high_critical": 50,
            },
            "PM1.0": {
                "low_medium": 0,
                "high_medium": 20,
                "high_high": 30,
                "high_critical": 45,
            },
            "Pressure[hPa]": {
                "low_critical": 900,
                "low_high": 950,
                "high_medium": 1050,
                "high_high": 1100,
                "high_critical": 1150,
            },
        }

    def detect_threshold_anomalies(self, data: Dict[str, Any]) -> List[AnomalyAlert]:
        """Detect anomalies based on predefined thresholds"""
        alerts = []
        timestamp = datetime.now()

        for sensor, value in data.items():
            if sensor not in self.thresholds or value is None:
                continue

            try:
                value = float(value)
                thresholds = self.thresholds[sensor]

                # Check critical thresholds
                if "low_critical" in thresholds and value < thresholds["low_critical"]:
                    alerts.append(
                        AnomalyAlert(
                            timestamp=timestamp,
                            sensor=sensor,
                            value=value,
                            threshold=thresholds["low_critical"],
                            severity="CRITICAL",
                            message=f"Critically low {sensor}: {value}",
                            alert_type="THRESHOLD",
                        )
                    )
                elif (
                    "high_critical" in thresholds
                    and value > thresholds["high_critical"]
                ):
                    alerts.append(
                        AnomalyAlert(
                            timestamp=timestamp,
                            sensor=sensor,
                            value=value,
                            threshold=thresholds["high_critical"],
                            severity="CRITICAL",
                            message=f"Critically high {sensor}: {value}",
                            alert_type="THRESHOLD",
                        )
                    )
                # Check high thresholds
                elif "low_high" in thresholds and value < thresholds["low_high"]:
                    alerts.append(
                        AnomalyAlert(
                            timestamp=timestamp,
                            sensor=sensor,
                            value=value,
                            threshold=thresholds["low_high"],
                            severity="HIGH",
                            message=f"Low {sensor}: {value}",
                            alert_type="THRESHOLD",
                        )
                    )
                elif "high_high" in thresholds and value > thresholds["high_high"]:
                    alerts.append(
                        AnomalyAlert(
                            timestamp=timestamp,
                            sensor=sensor,
                            value=value,
                            threshold=thresholds["high_high"],
                            severity="HIGH",
                            message=f"High {sensor}: {value}",
                            alert_type="THRESHOLD",
                        )
                    )
                # Check medium thresholds
                elif "high_medium" in thresholds and value > thresholds["high_medium"]:
                    alerts.append(
                        AnomalyAlert(
                            timestamp=timestamp,
                            sensor=sensor,
                            value=value,
                            threshold=thresholds["high_medium"],
                            severity="MEDIUM",
                            message=f"Elevated {sensor}: {value}",
                            alert_type="THRESHOLD",
                        )
                    )

            except (ValueError, TypeError):
                logger.warning(f"Invalid value for {sensor}: {value}")

        return alerts

    def detect_statistical_anomalies(
        self, data: Dict[str, Any], z_threshold: float = 3.0
    ) -> List[AnomalyAlert]:
        """Detect anomalies using statistical methods (Z-score)"""
        alerts = []
        timestamp = datetime.now()

        for sensor, value in data.items():
            if sensor not in self.rolling_stats or value is None:
                continue

            try:
                value = float(value)
                stats = self.rolling_stats[sensor]

                # Update rolling statistics
                stats.add_value(value)

                # Need sufficient data for statistical analysis
                if len(stats.values) < 30:
                    continue

                mean = stats.get_mean()
                std = stats.get_std()

                if mean is not None and std is not None and std > 0:
                    z_score = abs(value - mean) / std

                    if z_score > z_threshold:
                        severity = "HIGH" if z_score > 4.0 else "MEDIUM"
                        alerts.append(
                            AnomalyAlert(
                                timestamp=timestamp,
                                sensor=sensor,
                                value=value,
                                threshold=z_threshold,
                                severity=severity,
                                message=f"Statistical anomaly in {sensor}: {value} (Z-score: {z_score:.2f})",
                                alert_type="STATISTICAL",
                            )
                        )

            except (ValueError, TypeError):
                logger.warning(f"Invalid value for {sensor}: {value}")

        return alerts

    def detect_fire_patterns(self, data: Dict[str, Any]) -> List[AnomalyAlert]:
        """Detect fire-related patterns in sensor data"""
        alerts = []
        timestamp = datetime.now()

        try:
            # Extract relevant values
            temp = float(data.get("Temperature[C]", 0))
            tvoc = float(data.get("TVOC[ppb]", 0))
            eco2 = float(data.get("eCO2[ppm]", 0))
            pm25 = float(data.get("PM2.5", 0))
            fire_alarm = int(data.get("Fire Alarm", 0))

            # Direct fire alarm
            if fire_alarm == 1:
                alerts.append(
                    AnomalyAlert(
                        timestamp=timestamp,
                        sensor="Fire Alarm",
                        value=fire_alarm,
                        threshold=1,
                        severity="CRITICAL",
                        message="FIRE ALARM ACTIVATED!",
                        alert_type="PATTERN",
                    )
                )

            # Fire pattern detection
            fire_indicators = 0

            if temp > 45:  # High temperature
                fire_indicators += 1
            if tvoc > 800:  # High volatile organic compounds
                fire_indicators += 1
            if eco2 > 800:  # High CO2
                fire_indicators += 1
            if pm25 > 30:  # High particulate matter
                fire_indicators += 1

            if fire_indicators >= 3:
                alerts.append(
                    AnomalyAlert(
                        timestamp=timestamp,
                        sensor="Fire Pattern",
                        value=fire_indicators,
                        threshold=3,
                        severity="CRITICAL",
                        message=f"Fire pattern detected: {fire_indicators}/4 indicators active",
                        alert_type="PATTERN",
                    )
                )
            elif fire_indicators >= 2:
                alerts.append(
                    AnomalyAlert(
                        timestamp=timestamp,
                        sensor="Fire Pattern",
                        value=fire_indicators,
                        threshold=2,
                        severity="HIGH",
                        message=f"Potential fire risk: {fire_indicators}/4 indicators active",
                        alert_type="PATTERN",
                    )
                )

        except (ValueError, TypeError) as e:
            logger.warning(f"Error in fire pattern detection: {e}")

        return alerts

    def detect_all_anomalies(self, data: Dict[str, Any]) -> List[AnomalyAlert]:
        """Run all anomaly detection algorithms"""
        all_alerts = []

        # Threshold-based detection
        all_alerts.extend(self.detect_threshold_anomalies(data))

        # Statistical anomaly detection
        all_alerts.extend(self.detect_statistical_anomalies(data))

        # Fire pattern detection
        all_alerts.extend(self.detect_fire_patterns(data))

        return all_alerts


# Global detector instance
detector = SmokeAnomalyDetector()


def detect_anomalies(data: Dict[str, Any]) -> List[str]:
    """
    Main function for anomaly detection (backward compatibility)

    Args:
        data: Sensor data dictionary

    Returns:
        List of alert messages
    """
    alerts = detector.detect_all_anomalies(data)
    return [alert.message for alert in alerts]


def get_detailed_anomalies(data: Dict[str, Any]) -> List[AnomalyAlert]:
    """
    Get detailed anomaly information

    Args:
        data: Sensor data dictionary

    Returns:
        List of AnomalyAlert objects
    """
    return detector.detect_all_anomalies(data)
