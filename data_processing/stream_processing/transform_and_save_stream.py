import os
import json
import logging
import time
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import NULL_MARKER, GROUP_ID, HISTORICAL_DATA_FILE
from config.env_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_SMOKE
from data_processing import utils
from data_processing.stream_processing.metrics_streaming import (
    get_metrics_collector,
    start_metrics_logging,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("stream_processing.log"), logging.StreamHandler()],
)
logger = logging.getLogger("stream_processing")


columns = utils.get_kaggle_data_headers()


def validate_message(message):
    """Validate incoming message structure and data types"""
    required_fields = [
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

    # Check if message has all required fields
    missing_fields = []
    for field in required_fields:
        if field not in message:
            missing_fields.append(field)

    if missing_fields:
        logger.warning(f"Missing required fields: {missing_fields}")
        return False

    # Validate numeric data types for sensor readings
    numeric_fields = [
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

    for field in numeric_fields:
        if message.get(field) is not None:
            try:
                float(message[field])
            except (ValueError, TypeError):
                logger.warning(f"Invalid data type for {field}: {message[field]}")
                return False

    return True


def detect_anomalies(data):
    """Basic anomaly detection for sensor readings"""
    alerts = []

    try:
        temp = float(data.get("Temperature[C]", 0))
        humidity = float(data.get("Humidity[%]", 0))
        tvoc = float(data.get("TVOC[ppb]", 0))
        eco2 = float(data.get("eCO2[ppm]", 0))
        pm25 = float(data.get("PM2.5", 0))
        fire_alarm = data.get("Fire Alarm", 0)

        # Temperature thresholds
        if temp > 50:
            alerts.append(f"HIGH TEMPERATURE ALERT: {temp}°C")
        elif temp < -10:
            alerts.append(f"LOW TEMPERATURE ALERT: {temp}°C")

        # Humidity thresholds
        if humidity > 90:
            alerts.append(f"HIGH HUMIDITY ALERT: {humidity}%")
        elif humidity < 10:
            alerts.append(f"LOW HUMIDITY ALERT: {humidity}%")

        # Air quality thresholds
        if tvoc > 1000:
            alerts.append(f"HIGH TVOC ALERT: {tvoc} ppb")
        if eco2 > 1000:
            alerts.append(f"HIGH eCO2 ALERT: {eco2} ppm")
        if pm25 > 35:
            alerts.append(f"HIGH PM2.5 ALERT: {pm25} μg/m³")

        # Fire alarm
        if fire_alarm == 1:
            alerts.append("FIRE ALARM TRIGGERED!")

    except (ValueError, TypeError) as e:
        logger.error(f"Error in anomaly detection: {e}")

    return alerts


def save_historical_data(row, output_csv_file: str):
    """Save data into csv file row by row"""
    # If output_csv file doesn't exist or it's empty then it is the first time to write sth into this file
    first_time_flg = (
        not os.path.exists(output_csv_file) or os.path.getsize(output_csv_file) == 0
    )
    with open(output_csv_file, "a", encoding="utf-8") as f:
        # If it is the first time to write sth into this file, then write the header first
        if first_time_flg:
            f.write(",".join(columns) + "\n")  # Write header
        f.write(",".join(row) + "\n")
        f.flush()  # flush to disk immediately


def consume_streaming_data(topic, output_csv, group_id):
    """
    Consume messages from Kafka topic with validation, anomaly detection, and error handling.
    """
    max_retries = 5
    retry_count = 0

    # Initialize metrics collection
    metrics_collector = get_metrics_collector()
    start_metrics_logging(interval_seconds=60)  # Log metrics every minute

    while retry_count < max_retries:
        try:
            # Initialize Kafka consumer
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset="earliest",  # start from beginning if no offset
                enable_auto_commit=True,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            logger.info(
                f"Successfully connected to Kafka. Consuming from topic '{topic}' and writing to '{output_csv}'..."
            )
            retry_count = 0  # Reset retry count on successful connection

            # Consume messages continuously
            for message in consumer:
                start_time = time.time()
                try:
                    data = message.value  # a dict decoded from JSON

                    # Validate message
                    if not validate_message(data):
                        logger.warning("Skipping invalid message")
                        metrics_collector.record_message_failed()
                        continue

                    # Detect anomalies
                    alerts = detect_anomalies(data)
                    if alerts:
                        metrics_collector.record_anomaly_detected()
                        for alert in alerts:
                            logger.warning(f"ANOMALY DETECTED: {alert}")
                            metrics_collector.record_alert_triggered()

                    # Prepare row values in correct column order
                    row = []
                    for col in columns:
                        val = data.get(col)
                        val = NULL_MARKER if val is None else val
                        row.append(str(val))

                    save_historical_data(row, output_csv)

                    # Record successful processing
                    processing_time = (
                        time.time() - start_time
                    ) * 1000  # Convert to milliseconds
                    quality_score = (
                        1.0 if len(alerts) == 0 else 0.8
                    )  # Lower quality if anomalies detected
                    metrics_collector.record_message_processed(
                        processing_time, quality_score
                    )

                    logger.debug(
                        f"Processed message: {len(row)} fields in {processing_time:.2f}ms"
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    metrics_collector.record_message_failed()
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    metrics_collector.record_message_failed()
                    continue

        except NoBrokersAvailable:
            retry_count += 1
            logger.warning(
                f"Kafka brokers not available. Retry {retry_count}/{max_retries} in 10s"
            )
            if retry_count >= max_retries:
                logger.error(f"Failed to connect to Kafka after {max_retries} attempts")
                raise
            time.sleep(10)
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise


if __name__ == "__main__":
    historical_data_file_path = build_relative_path(DATA_DIR, HISTORICAL_DATA_FILE)
    print(f"historical_data_file_path: {historical_data_file_path}")
    consume_streaming_data(
        KAFKA_TOPIC_SMOKE, historical_data_file_path, group_id=GROUP_ID
    )
