"""
Production-ready Spark Streaming processor for real-time IoT smoke detection data analytics.

This module provides comprehensive real-time analytics including:
- Windowed aggregations and statistics
- Real-time anomaly detection
- Multi-level alerting system
- Data quality monitoring
- Performance metrics tracking
- Fault-tolerant stream processing
- Integration with ML models for predictions

Features:
- Configurable window sizes and slide intervals
- Multiple output formats (console, files, Kafka)
- Comprehensive error handling and recovery
- Memory-efficient processing with watermarking
- Real-time dashboard data generation
- Historical data archival

Classes:
    SparkStreamProcessor: Main processor class for stream analytics
    AlertManager: Handles multi-level alerting
    DataQualityMonitor: Monitors data quality metrics
    PerformanceTracker: Tracks processing performance

Functions:
    create_spark_session: Creates optimized Spark session
    get_sensor_schema: Defines IoT sensor data schema
    process_analytics_batch: Processes windowed analytics batches
    start_streaming_analytics: Main streaming entry point
"""

import sys
import os
import argparse
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # Fixed path depth
sys.path.append(str(project_root))

import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    window,
    avg,
    count,
    col,
    from_json,
    when,
    max as spark_max,
    min as spark_min,
    stddev,
    current_timestamp,
    lit,
    expr,
    sum as spark_sum,
    first,
    last,
    percentile_approx,
    variance,
    skewness,
    kurtosis,
    collect_list,
    size,
    unix_timestamp,
    to_timestamp,
    date_format,
    hour,
    minute,
    dayofweek,
)
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType,
    TimestampType,
    BooleanType,
    ArrayType,
)
from pyspark.sql.streaming import StreamingQuery

try:
    from config.env_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_SMOKE
except ImportError:
    # Fallback configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_SMOKE = os.getenv("KAFKA_TOPIC_SMOKE", "smoke_sensor_data")

# Import requests for ML API calls
try:
    import requests
except ImportError:
    logger.warning("requests library not available - ML API calls will be disabled")
    requests = None


# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    handlers=[logging.FileHandler("spark_streaming.log"), logging.StreamHandler()],
)
logger = logging.getLogger("spark_streaming")


@dataclass
class StreamingConfig:
    """Configuration for Spark streaming processor."""

    kafka_bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS
    kafka_topic: str = KAFKA_TOPIC_SMOKE
    window_duration: str = "5 minutes"
    slide_duration: str = "1 minute"
    watermark_delay: str = "10 minutes"
    checkpoint_location: str = "/app/data/checkpoints"
    output_path: str = "/app/data/processed_stream"
    max_files_per_trigger: int = 1
    trigger_interval: str = "30 seconds"
    enable_console_output: bool = True
    enable_file_output: bool = True
    enable_kafka_output: bool = False
    output_kafka_topic: str = "smoke_analytics"
    enable_ml_predictions: bool = True
    ml_model_path: str = "/app/ml/models/best_model.pkl"


@dataclass
class AlertThresholds:
    """Alert thresholds for sensor values."""

    temperature_high: float = 50.0
    temperature_low: float = -10.0
    temperature_critical: float = 80.0
    humidity_high: float = 90.0
    humidity_low: float = 10.0
    tvoc_high: float = 1000.0
    tvoc_critical: float = 2000.0
    eco2_high: float = 1000.0
    eco2_critical: float = 1500.0
    pm25_high: float = 35.0
    pm25_critical: float = 75.0
    pressure_high: float = 1050.0
    pressure_low: float = 950.0


@dataclass
class ProcessingMetrics:
    """Metrics for stream processing performance."""

    batch_id: int
    processing_time: float
    input_rows: int
    output_rows: int
    timestamp: datetime
    memory_usage: float = 0.0
    cpu_usage: float = 0.0


@dataclass
class MLPredictionConfig:
    """Configuration for ML predictions in streaming."""

    ml_api_url: str = "http://ml_api:5000"
    enable_ml_predictions: bool = True
    prediction_threshold: float = 0.5
    batch_prediction_size: int = 100
    enable_prediction_caching: bool = True
    prediction_timeout: float = 5.0  # seconds
    api_retry_attempts: int = 3
    api_retry_delay: float = 1.0  # seconds


@dataclass
class MLPredictionResult:
    """Result from ML prediction."""

    prediction: int
    prediction_label: str
    confidence: float
    probability: Dict[str, float]
    model_info: Dict[str, Any]
    processing_time: float
    timestamp: str
    error: Optional[str] = None


class AlertManager:
    """Manages multi-level alerting for sensor data."""

    def __init__(self, thresholds: AlertThresholds = AlertThresholds()):
        self.thresholds = thresholds
        self.alert_history = []

    def evaluate_alerts(self, analytics_row) -> List[Dict[str, Any]]:
        """Evaluate analytics data and generate alerts."""
        alerts = []

        # Temperature alerts
        if analytics_row.avg_temperature:
            temp = analytics_row.avg_temperature
            if temp > self.thresholds.temperature_critical:
                alerts.append(
                    {
                        "level": "CRITICAL",
                        "type": "TEMPERATURE",
                        "value": temp,
                        "threshold": self.thresholds.temperature_critical,
                        "message": f"Critical temperature: {temp:.2f}°C",
                    }
                )
            elif temp > self.thresholds.temperature_high:
                alerts.append(
                    {
                        "level": "HIGH",
                        "type": "TEMPERATURE",
                        "value": temp,
                        "threshold": self.thresholds.temperature_high,
                        "message": f"High temperature: {temp:.2f}°C",
                    }
                )
            elif temp < self.thresholds.temperature_low:
                alerts.append(
                    {
                        "level": "LOW",
                        "type": "TEMPERATURE",
                        "value": temp,
                        "threshold": self.thresholds.temperature_low,
                        "message": f"Low temperature: {temp:.2f}°C",
                    }
                )

        # Air quality alerts
        if analytics_row.avg_tvoc:
            tvoc = analytics_row.avg_tvoc
            if tvoc > self.thresholds.tvoc_critical:
                alerts.append(
                    {
                        "level": "CRITICAL",
                        "type": "TVOC",
                        "value": tvoc,
                        "threshold": self.thresholds.tvoc_critical,
                        "message": f"Critical TVOC level: {tvoc:.2f} ppb",
                    }
                )
            elif tvoc > self.thresholds.tvoc_high:
                alerts.append(
                    {
                        "level": "HIGH",
                        "type": "TVOC",
                        "value": tvoc,
                        "threshold": self.thresholds.tvoc_high,
                        "message": f"High TVOC level: {tvoc:.2f} ppb",
                    }
                )

        # PM2.5 alerts
        if analytics_row.avg_pm25:
            pm25 = analytics_row.avg_pm25
            if pm25 > self.thresholds.pm25_critical:
                alerts.append(
                    {
                        "level": "CRITICAL",
                        "type": "PM2.5",
                        "value": pm25,
                        "threshold": self.thresholds.pm25_critical,
                        "message": f"Critical PM2.5 level: {pm25:.2f} μg/m³",
                    }
                )
            elif pm25 > self.thresholds.pm25_high:
                alerts.append(
                    {
                        "level": "HIGH",
                        "type": "PM2.5",
                        "value": pm25,
                        "threshold": self.thresholds.pm25_high,
                        "message": f"High PM2.5 level: {pm25:.2f} μg/m³",
                    }
                )

        # Fire alarm alerts
        if analytics_row.fire_alarm_count and analytics_row.fire_alarm_count > 0:
            alerts.append(
                {
                    "level": "CRITICAL",
                    "type": "FIRE_ALARM",
                    "value": analytics_row.fire_alarm_count,
                    "threshold": 0,
                    "message": f"Fire alarm triggered: {analytics_row.fire_alarm_count} alarms",
                }
            )

        return alerts

    def log_alerts(self, alerts: List[Dict[str, Any]], window_info: str):
        """Log alerts with appropriate severity levels."""
        for alert in alerts:
            alert_msg = f"{alert['message']} in {window_info}"

            if alert["level"] == "CRITICAL":
                logger.critical(f"🚨 {alert_msg}")
            elif alert["level"] == "HIGH":
                logger.warning(f"⚠️  {alert_msg}")
            elif alert["level"] == "LOW":
                logger.warning(f"❄️  {alert_msg}")

            # Store in history
            self.alert_history.append(
                {**alert, "timestamp": datetime.now(), "window": window_info}
            )


class DataQualityMonitor:
    """Monitors data quality metrics for incoming sensor data."""

    def __init__(self):
        self.quality_metrics = {}

    def evaluate_data_quality(self, analytics_row) -> Dict[str, Any]:
        """Evaluate data quality metrics."""
        quality_score = 100.0
        issues = []

        # Check for missing data indicators
        if analytics_row.record_count < 10:
            quality_score -= 20
            issues.append("Low data volume")

        # Check for sensor variance (too low might indicate stuck sensors)
        if hasattr(analytics_row, "temp_stddev") and analytics_row.temp_stddev:
            if analytics_row.temp_stddev < 0.1:
                quality_score -= 15
                issues.append("Low temperature variance - possible stuck sensor")

        # Check for extreme values
        if analytics_row.max_temperature and analytics_row.max_temperature > 100:
            quality_score -= 25
            issues.append("Extreme temperature readings")

        if analytics_row.min_temperature and analytics_row.min_temperature < -50:
            quality_score -= 25
            issues.append("Extreme low temperature readings")

        return {
            "quality_score": max(0, quality_score),
            "issues": issues,
            "data_completeness": min(100, (analytics_row.record_count / 100) * 100),
        }


class MLPredictor:
    """Handles ML predictions for streaming data via API calls."""

    def __init__(self, config: MLPredictionConfig = MLPredictionConfig()):
        self.config = config
        self.prediction_cache = {}
        self.prediction_count = 0
        self.fire_detection_count = 0
        self.api_available = False
        self.last_health_check = None

    def initialize_ml_api(self) -> bool:
        """Initialize ML API connection."""
        try:
            if not self.config.enable_ml_predictions:
                logger.info("ML predictions disabled in configuration")
                return False

            if not requests:
                logger.warning(
                    "❌ requests library not available - ML API calls disabled"
                )
                return False

            logger.info(f"Connecting to ML API: {self.config.ml_api_url}")

            # Test API health
            health_url = f"{self.config.ml_api_url}/health"
            response = requests.get(health_url, timeout=self.config.prediction_timeout)

            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ ML API is healthy:")
                logger.info(f"   Status: {health_data.get('status', 'Unknown')}")
                logger.info(
                    f"   Model Loaded: {health_data.get('model_loaded', False)}"
                )

                # Get model info
                try:
                    info_url = f"{self.config.ml_api_url}/model/info"
                    info_response = requests.get(
                        info_url, timeout=self.config.prediction_timeout
                    )
                    if info_response.status_code == 200:
                        model_info = info_response.json()
                        logger.info(
                            f"   Model Type: {model_info.get('model_type', 'Unknown')}"
                        )
                        logger.info(
                            f"   Features: {model_info.get('feature_count', 0)}"
                        )
                except Exception as e:
                    logger.debug(f"Could not get model info: {e}")

                self.api_available = True
                self.last_health_check = datetime.now()
                return True
            else:
                logger.warning(f"❌ ML API health check failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error connecting to ML API: {e}")
            return False

    def predict_batch(
        self, sensor_data_list: List[Dict[str, Any]]
    ) -> List[MLPredictionResult]:
        """Make ML predictions on a batch of sensor data via API."""
        if not self.api_available or not self.config.enable_ml_predictions:
            return []

        results = []
        start_time = time.time()

        try:
            for sensor_data in sensor_data_list:
                prediction_result = self._predict_single_api(sensor_data)
                results.append(prediction_result)

                # Update counters
                self.prediction_count += 1
                if prediction_result.prediction == 1:
                    self.fire_detection_count += 1

            processing_time = time.time() - start_time
            logger.debug(
                f"🤖 Processed {len(sensor_data_list)} ML predictions in {processing_time:.3f}s"
            )

        except Exception as e:
            logger.error(f"❌ Error in batch ML prediction: {e}")
            # Return error results for all inputs
            for sensor_data in sensor_data_list:
                results.append(
                    MLPredictionResult(
                        prediction=0,
                        prediction_label="Error",
                        confidence=0.0,
                        probability={"no_fire": 0.5, "fire": 0.5},
                        model_info={},
                        processing_time=0.0,
                        timestamp=datetime.now().isoformat(),
                        error=str(e),
                    )
                )

        return results

    def _predict_single_api(self, sensor_data: Dict[str, Any]) -> MLPredictionResult:
        """Make ML prediction on single sensor reading."""
        start_time = time.time()

        try:
            # Check cache if enabled
            if self.config.enable_prediction_caching:
                cache_key = self._generate_cache_key(sensor_data)
                if cache_key in self.prediction_cache:
                    cached_result = self.prediction_cache[cache_key]
                    cached_result.timestamp = datetime.now().isoformat()
                    return cached_result

            # Make API prediction with retries
            prediction_result = self._call_prediction_api(sensor_data)
            processing_time = time.time() - start_time

            # Convert to MLPredictionResult
            ml_result = MLPredictionResult(
                prediction=prediction_result.get("prediction", 0),
                prediction_label=prediction_result.get("prediction_label", "Unknown"),
                confidence=prediction_result.get("confidence", 0.0),
                probability=prediction_result.get(
                    "probability", {"no_fire": 0.5, "fire": 0.5}
                ),
                model_info=prediction_result.get("model_info", {}),
                processing_time=processing_time,
                timestamp=prediction_result.get(
                    "timestamp", datetime.now().isoformat()
                ),
                error=prediction_result.get("error"),
            )

            # Cache result if enabled
            if self.config.enable_prediction_caching and not ml_result.error:
                cache_key = self._generate_cache_key(sensor_data)
                self.prediction_cache[cache_key] = ml_result

                # Limit cache size
                if len(self.prediction_cache) > 1000:
                    # Remove oldest entries
                    oldest_keys = list(self.prediction_cache.keys())[:100]
                    for key in oldest_keys:
                        del self.prediction_cache[key]

            return ml_result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Error in single ML prediction: {e}")

            return MLPredictionResult(
                prediction=0,
                prediction_label="Error",
                confidence=0.0,
                probability={"no_fire": 0.5, "fire": 0.5},
                model_info={},
                processing_time=processing_time,
                timestamp=datetime.now().isoformat(),
                error=str(e),
            )

    def _call_prediction_api(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call ML API for prediction with retry logic."""
        predict_url = f"{self.config.ml_api_url}/predict"

        for attempt in range(self.config.api_retry_attempts):
            try:
                response = requests.post(
                    predict_url,
                    json=sensor_data,
                    timeout=self.config.prediction_timeout,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"ML API returned status {response.status_code}: {response.text}"
                    )
                    if attempt == self.config.api_retry_attempts - 1:
                        return {"error": f"API error: {response.status_code}"}

            except requests.exceptions.Timeout:
                logger.warning(
                    f"ML API timeout (attempt {attempt + 1}/{self.config.api_retry_attempts})"
                )
                if attempt == self.config.api_retry_attempts - 1:
                    return {"error": "API timeout"}

            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"ML API connection error (attempt {attempt + 1}/{self.config.api_retry_attempts})"
                )
                if attempt == self.config.api_retry_attempts - 1:
                    self.api_available = False
                    return {"error": "API connection failed"}

            except Exception as e:
                logger.error(f"ML API call error: {e}")
                return {"error": str(e)}

            # Wait before retry
            if attempt < self.config.api_retry_attempts - 1:
                time.sleep(self.config.api_retry_delay)

        return {"error": "Max retries exceeded"}

    def _generate_cache_key(self, sensor_data: Dict[str, Any]) -> str:
        """Generate cache key for sensor data."""
        # Use rounded values for caching to increase hit rate
        key_data = {}
        for key, value in sensor_data.items():
            if isinstance(value, (int, float)):
                key_data[key] = round(float(value), 2)
            else:
                key_data[key] = value

        return str(hash(frozenset(key_data.items())))

    def get_prediction_stats(self) -> Dict[str, Any]:
        """Get ML prediction statistics."""
        return {
            "total_predictions": self.prediction_count,
            "fire_detections": self.fire_detection_count,
            "fire_detection_rate": (
                self.fire_detection_count / self.prediction_count
                if self.prediction_count > 0
                else 0.0
            ),
            "cache_size": len(self.prediction_cache),
            "model_loaded": self.predictor is not None
            and self.predictor.model_loader.is_loaded,
            "last_model_load": (
                self.last_model_load_time.isoformat()
                if self.last_model_load_time
                else None
            ),
        }


def create_spark_session(
    app_name: str = "SmokeDetectionStreamProcessing",
) -> SparkSession:
    """
    Create and configure optimized Spark session for streaming.

    Args:
        app_name: Name for the Spark application

    Returns:
        Configured SparkSession instance
    """
    return (
        SparkSession.builder.appName(app_name)
        .config(
            "spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0"
        )
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.adaptive.skewJoin.enabled", "true")
        .config("spark.sql.streaming.metricsEnabled", "true")
        .config("spark.sql.streaming.ui.enabled", "true")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.adaptive.advisoryPartitionSizeInBytes", "128MB")
        .getOrCreate()
    )


def get_sensor_schema() -> StructType:
    """
    Define comprehensive schema for IoT sensor data.

    Returns:
        StructType schema for sensor data including all sensor fields
        and optional metadata fields for device tracking
    """
    return StructType(
        [
            StructField("Temperature[C]", DoubleType(), True),
            StructField("Humidity[%]", DoubleType(), True),
            StructField("TVOC[ppb]", DoubleType(), True),
            StructField("eCO2[ppm]", DoubleType(), True),
            StructField("Raw H2", DoubleType(), True),
            StructField("Raw Ethanol", DoubleType(), True),
            StructField("Pressure[hPa]", DoubleType(), True),
            StructField("PM1.0", DoubleType(), True),
            StructField("PM2.5", DoubleType(), True),
            StructField("NC0.5", DoubleType(), True),
            StructField("NC1.0", DoubleType(), True),
            StructField("NC2.5", DoubleType(), True),
            StructField("CNT", IntegerType(), True),
            StructField("Fire Alarm", IntegerType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("device_id", StringType(), True),
            StructField("location", StringType(), True),
        ]
    )


class SparkStreamProcessor:
    """
    Main Spark streaming processor for IoT smoke detection analytics.

    This class orchestrates the entire streaming pipeline including:
    - Data ingestion from Kafka
    - Real-time analytics computation
    - Alert generation and management
    - Data quality monitoring
    - Performance tracking
    """

    def __init__(
        self,
        config: StreamingConfig = StreamingConfig(),
        ml_config: MLPredictionConfig = MLPredictionConfig(),
    ):
        self.config = config
        self.ml_config = ml_config
        self.alert_manager = AlertManager()
        self.quality_monitor = DataQualityMonitor()
        self.ml_predictor = MLPredictor(ml_config)
        self.spark = None
        self.active_queries = []
        self.processing_metrics = []

    def initialize_spark_session(self):
        """Initialize Spark session with configuration."""
        self.spark = create_spark_session()
        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("Spark session initialized successfully")

        # Initialize ML model if enabled
        if self.ml_config.enable_ml_predictions:
            ml_success = self.ml_predictor.initialize_ml_model()
            if ml_success:
                logger.info("🤖 ML model integration enabled")
            else:
                logger.warning(
                    "⚠️ ML model integration failed - continuing without ML predictions"
                )

    def create_kafka_stream(self) -> DataFrame:
        """Create Kafka streaming DataFrame."""
        return (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self.config.kafka_bootstrap_servers)
            .option("subscribe", self.config.kafka_topic)
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .load()
        )

    def parse_sensor_data(self, kafka_df: DataFrame) -> DataFrame:
        """Parse JSON sensor data from Kafka."""
        schema = get_sensor_schema()

        return (
            kafka_df.selectExpr(
                "CAST(value AS STRING) as json_data", "timestamp as kafka_timestamp"
            )
            .select(
                from_json(col("json_data"), schema).alias("data"), "kafka_timestamp"
            )
            .select("data.*", "kafka_timestamp")
            .withColumn("processing_timestamp", current_timestamp())
        )

    def create_windowed_analytics(self, parsed_df: DataFrame) -> DataFrame:
        """Create windowed analytics with comprehensive metrics."""
        return (
            parsed_df.withWatermark("processing_timestamp", self.config.watermark_delay)
            .groupBy(
                window(
                    col("processing_timestamp"),
                    self.config.window_duration,
                    self.config.slide_duration,
                )
            )
            .agg(
                # Basic statistics
                avg("Temperature[C]").alias("avg_temperature"),
                avg("Humidity[%]").alias("avg_humidity"),
                avg("TVOC[ppb]").alias("avg_tvoc"),
                avg("eCO2[ppm]").alias("avg_eco2"),
                avg("PM2.5").alias("avg_pm25"),
                avg("PM1.0").alias("avg_pm10"),
                avg("Pressure[hPa]").alias("avg_pressure"),
                avg("Raw H2").alias("avg_h2"),
                avg("Raw Ethanol").alias("avg_ethanol"),
                # Min/Max values
                spark_max("Temperature[C]").alias("max_temperature"),
                spark_min("Temperature[C]").alias("min_temperature"),
                spark_max("Humidity[%]").alias("max_humidity"),
                spark_min("Humidity[%]").alias("min_humidity"),
                spark_max("TVOC[ppb]").alias("max_tvoc"),
                spark_max("PM2.5").alias("max_pm25"),
                # Statistical measures
                stddev("Temperature[C]").alias("temp_stddev"),
                stddev("Humidity[%]").alias("humidity_stddev"),
                stddev("TVOC[ppb]").alias("tvoc_stddev"),
                variance("Temperature[C]").alias("temp_variance"),
                # Advanced statistics
                percentile_approx("Temperature[C]", 0.5).alias("temp_median"),
                percentile_approx("TVOC[ppb]", 0.95).alias("tvoc_95th_percentile"),
                # Counts and flags
                count("*").alias("record_count"),
                count(when(col("Fire Alarm") == 1, 1)).alias("fire_alarm_count"),
                spark_sum(when(col("Fire Alarm") == 1, 1).otherwise(0)).alias(
                    "total_fire_alarms"
                ),
                # Data quality metrics
                count(when(col("Temperature[C]").isNull(), 1)).alias(
                    "null_temperature_count"
                ),
                count(when(col("TVOC[ppb]").isNull(), 1)).alias("null_tvoc_count"),
                # Device tracking
                collect_list("device_id").alias("device_ids"),
                collect_list("location").alias("locations"),
            )
        )


def process_analytics_batch(df: DataFrame, epoch_id: int):
    """
    Enhanced batch processing function with comprehensive analytics and alerting.

    Args:
        df: DataFrame containing windowed analytics
        epoch_id: Batch epoch identifier
    """
    start_time = time.time()

    try:
        if df.count() > 0:
            logger.info(
                f"Processing batch {epoch_id} with {df.count()} analytics windows"
            )

            # Initialize managers for this batch
            alert_manager = AlertManager()
            quality_monitor = DataQualityMonitor()
            ml_predictor = MLPredictor()  # Create ML predictor for this batch

            # Initialize ML API if not already done
            if ml_predictor.config.enable_ml_predictions:
                ml_predictor.initialize_ml_api()

            # Collect analytics for processing
            analytics_rows = df.collect()

            for row in analytics_rows:
                window_start = row.window.start
                window_end = row.window.end
                window_info = f"{window_start} - {window_end}"

                # Evaluate alerts
                alerts = alert_manager.evaluate_alerts(row)
                if alerts:
                    alert_manager.log_alerts(alerts, window_info)

                # Evaluate data quality
                quality_metrics = quality_monitor.evaluate_data_quality(row)
                if quality_metrics["quality_score"] < 80:
                    logger.warning(
                        f"Data quality issues in {window_info}: "
                        f"Score: {quality_metrics['quality_score']:.1f}%, "
                        f"Issues: {', '.join(quality_metrics['issues'])}"
                    )

                # Prepare sensor data for ML prediction
                sensor_data = {
                    "Temperature[C]": row.avg_temperature,
                    "Humidity[%]": row.avg_humidity,
                    "TVOC[ppb]": row.avg_tvoc,
                    "eCO2[ppm]": row.avg_eco2,
                    "PM2.5": row.avg_pm25,
                    "PM1.0": row.avg_pm10,
                    "Pressure[hPa]": row.avg_pressure,
                    "Raw H2": row.avg_h2,
                    "Raw Ethanol": row.avg_ethanol,
                    "Fire Alarm": 1 if row.fire_alarm_count > 0 else 0,
                }

                # Make ML prediction on aggregated data
                ml_prediction = None
                if (
                    ml_predictor.config.enable_ml_predictions
                    and ml_predictor.api_available
                ):
                    try:
                        ml_prediction = ml_predictor._predict_single_api(sensor_data)

                        # Log ML prediction results
                        if ml_prediction.prediction == 1:
                            logger.warning(
                                f"🤖 ML FIRE PREDICTION: {ml_prediction.confidence:.2f} confidence "
                                f"in {window_info} (Label: {ml_prediction.prediction_label})"
                            )
                        else:
                            logger.debug(
                                f"🤖 ML prediction: {ml_prediction.prediction_label} "
                                f"({ml_prediction.confidence:.2f} confidence) in {window_info}"
                            )
                    except Exception as ml_error:
                        logger.error(
                            f"❌ ML prediction error in {window_info}: {ml_error}"
                        )

                # Log comprehensive analytics with ML results
                ml_info = ""
                if ml_prediction and not ml_prediction.error:
                    ml_info = f", ML: {ml_prediction.prediction_label} ({ml_prediction.confidence:.2f})"

                logger.info(
                    f"📊 Window Analytics ({window_info}): "
                    f"Records: {row.record_count}, "
                    f"Temp: {row.avg_temperature:.2f}°C (σ={row.temp_stddev:.2f}), "
                    f"Humidity: {row.avg_humidity:.2f}%, "
                    f"TVOC: {row.avg_tvoc:.2f}ppb (max={row.max_tvoc:.2f}), "
                    f"PM2.5: {row.avg_pm25:.2f}μg/m³, "
                    f"Fire Alarms: {row.fire_alarm_count}, "
                    f"Quality: {quality_metrics['quality_score']:.1f}%{ml_info}"
                )

                # Log device information if available
                if hasattr(row, "device_ids") and row.device_ids:
                    unique_devices = len(set(row.device_ids))
                    logger.debug(
                        f"Data from {unique_devices} unique devices in {window_info}"
                    )

            # Log ML prediction statistics
            if ml_predictor.config.enable_ml_predictions:
                ml_stats = ml_predictor.get_prediction_stats()
                logger.debug(
                    f"🤖 ML Stats - Total: {ml_stats['total_predictions']}, "
                    f"Fire Rate: {ml_stats['fire_detection_rate']:.2%}, "
                    f"Cache: {ml_stats['cache_size']}"
                )

        processing_time = time.time() - start_time
        logger.debug(f"Batch {epoch_id} processed in {processing_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Error processing batch {epoch_id}: {e}", exc_info=True)
        raise


def start_streaming_analytics(
    config: StreamingConfig = StreamingConfig(),
) -> SparkStreamProcessor:
    """
    Start comprehensive Spark streaming analytics with enhanced features including ML predictions.

    Args:
        config: Streaming configuration object

    Returns:
        SparkStreamProcessor instance
    """
    # Create ML configuration from streaming config
    ml_api_url = os.getenv("ML_API_URL", "http://ml_api:5000")
    ml_config = MLPredictionConfig(
        ml_api_url=ml_api_url,
        enable_ml_predictions=config.enable_ml_predictions,
        batch_prediction_size=100,
        enable_prediction_caching=True,
    )

    processor = SparkStreamProcessor(config, ml_config)

    try:
        # Initialize Spark session
        processor.initialize_spark_session()

        logger.info(f"🚀 Starting Spark streaming for topic: {config.kafka_topic}")
        logger.info(
            f"📊 Window: {config.window_duration}, Slide: {config.slide_duration}"
        )

        # Create streaming pipeline
        kafka_stream = processor.create_kafka_stream()
        parsed_stream = processor.parse_sensor_data(kafka_stream)
        analytics_stream = processor.create_windowed_analytics(parsed_stream)

        # Start analytics query
        analytics_query = (
            analytics_stream.writeStream.foreachBatch(process_analytics_batch)
            .outputMode("update")
            .option("checkpointLocation", f"{config.checkpoint_location}/analytics")
            .trigger(processingTime=config.trigger_interval)
            .start()
        )

        processor.active_queries.append(analytics_query)

        # Optional: Save raw data for historical analysis
        if config.enable_file_output:
            raw_data_query = (
                parsed_stream.writeStream.format("parquet")
                .option("path", f"{config.output_path}/raw_data")
                .option("checkpointLocation", f"{config.checkpoint_location}/raw_data")
                .partitionBy("device_id")
                .outputMode("append")
                .trigger(processingTime=config.trigger_interval)
                .start()
            )

            processor.active_queries.append(raw_data_query)

        # Optional: Console output for debugging
        if config.enable_console_output:
            console_query = (
                analytics_stream.writeStream.outputMode("update")
                .format("console")
                .option("truncate", "false")
                .option("numRows", 20)
                .trigger(processingTime=config.trigger_interval)
                .start()
            )

            processor.active_queries.append(console_query)

        logger.info(f"✅ Started {len(processor.active_queries)} streaming queries")

        # Set up graceful shutdown
        def signal_handler(signum, frame):
            logger.info("🛑 Received shutdown signal, stopping streaming...")
            for query in processor.active_queries:
                query.stop()
            processor.spark.stop()
            logger.info("✅ Streaming stopped gracefully")

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Wait for termination
        for query in processor.active_queries:
            query.awaitTermination()

    except Exception as e:
        logger.error(f"❌ Error in streaming processing: {e}", exc_info=True)
        raise
    finally:
        if processor.spark:
            processor.spark.stop()

    return processor


def main():
    """Main entry point with command line argument support."""
    parser = argparse.ArgumentParser(
        description="Spark Streaming Processor for IoT Smoke Detection"
    )

    parser.add_argument(
        "--kafka-servers",
        default=KAFKA_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--kafka-topic", default=KAFKA_TOPIC_SMOKE, help="Kafka topic to consume from"
    )
    parser.add_argument(
        "--window-duration", default="5 minutes", help="Window duration for analytics"
    )
    parser.add_argument(
        "--slide-duration", default="1 minute", help="Slide duration for windows"
    )
    parser.add_argument(
        "--checkpoint-location",
        default="/app/data/checkpoints",
        help="Checkpoint location for fault tolerance",
    )
    parser.add_argument(
        "--output-path",
        default="/app/data/processed_stream",
        help="Output path for processed data",
    )
    parser.add_argument(
        "--enable-console",
        action="store_true",
        help="Enable console output for debugging",
    )
    parser.add_argument(
        "--disable-file-output", action="store_true", help="Disable file output"
    )
    parser.add_argument(
        "--enable-ml",
        action="store_true",
        default=True,
        help="Enable ML predictions (default: True)",
    )
    parser.add_argument(
        "--disable-ml", action="store_true", help="Disable ML predictions"
    )
    parser.add_argument(
        "--ml-model-path",
        default="/app/ml/models/best_model.pkl",
        help="Path to ML model file",
    )

    args = parser.parse_args()

    # Create configuration from arguments
    config = StreamingConfig(
        kafka_bootstrap_servers=args.kafka_servers,
        kafka_topic=args.kafka_topic,
        window_duration=args.window_duration,
        slide_duration=args.slide_duration,
        checkpoint_location=args.checkpoint_location,
        output_path=args.output_path,
        enable_console_output=args.enable_console,
        enable_file_output=not args.disable_file_output,
        enable_ml_predictions=args.enable_ml and not args.disable_ml,
        ml_model_path=args.ml_model_path,
    )

    logger.info("🔥 Starting IoT Smoke Detection Stream Processor")
    logger.info(f"📋 Configuration: {config}")

    try:
        processor = start_streaming_analytics(config)
        logger.info("🎉 Stream processing completed successfully")
    except KeyboardInterrupt:
        logger.info("👋 Stream processing interrupted by user")
    except Exception as e:
        logger.error(f"💥 Stream processing failed: {e}")
        raise


if __name__ == "__main__":
    main()
