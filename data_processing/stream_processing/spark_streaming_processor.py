"""
Spark Streaming processor for real-time IoT smoke detection data analytics.
Provides windowed analytics and real-time anomaly detection.
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[3]
sys.path.append(str(project_root))

import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    window, avg, count, col, from_json, when, max as spark_max, min as spark_min,
    stddev, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
)
from config.env_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_SMOKE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spark_streaming.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("spark_streaming")


def create_spark_session():
    """Create and configure Spark session for streaming"""
    return SparkSession.builder \
        .appName("SmokeDetectionStreamProcessing") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()


def get_sensor_schema():
    """Define schema for IoT sensor data"""
    return StructType([
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
        StructField("timestamp", TimestampType(), True)
    ])


def process_analytics_batch(df, epoch_id):
    """Process each batch for real-time analytics and alerting"""
    if df.count() > 0:
        logger.info(f"Processing batch {epoch_id} with {df.count()} records")
        
        # Collect analytics for alerting
        analytics = df.collect()
        
        for row in analytics:
            window_start = row.window.start
            window_end = row.window.end
            
            # Temperature alerts
            if row.avg_temperature and row.avg_temperature > 50:
                logger.warning(f"HIGH TEMPERATURE ALERT: {row.avg_temperature:.2f}°C "
                             f"in window {window_start} - {window_end}")
            elif row.avg_temperature and row.avg_temperature < -10:
                logger.warning(f"LOW TEMPERATURE ALERT: {row.avg_temperature:.2f}°C "
                             f"in window {window_start} - {window_end}")
            
            # Air quality alerts
            if row.avg_tvoc and row.avg_tvoc > 1000:
                logger.warning(f"HIGH TVOC ALERT: {row.avg_tvoc:.2f} ppb "
                             f"in window {window_start} - {window_end}")
            
            if row.avg_eco2 and row.avg_eco2 > 1000:
                logger.warning(f"HIGH eCO2 ALERT: {row.avg_eco2:.2f} ppm "
                             f"in window {window_start} - {window_end}")
            
            if row.avg_pm25 and row.avg_pm25 > 35:
                logger.warning(f"HIGH PM2.5 ALERT: {row.avg_pm25:.2f} μg/m³ "
                             f"in window {window_start} - {window_end}")
            
            # Humidity alerts
            if row.avg_humidity and (row.avg_humidity > 90 or row.avg_humidity < 10):
                logger.warning(f"HUMIDITY ALERT: {row.avg_humidity:.2f}% "
                             f"in window {window_start} - {window_end}")
            
            # Fire alarm alerts
            if row.fire_alarm_count and row.fire_alarm_count > 0:
                logger.critical(f"FIRE ALARM TRIGGERED: {row.fire_alarm_count} alarms "
                              f"in window {window_start} - {window_end}")
            
            # Log general analytics
            logger.info(f"Window Analytics ({window_start} - {window_end}): "
                       f"Records: {row.record_count}, "
                       f"Avg Temp: {row.avg_temperature:.2f}°C, "
                       f"Avg Humidity: {row.avg_humidity:.2f}%, "
                       f"Avg TVOC: {row.avg_tvoc:.2f} ppb")


def start_streaming_analytics(topic=KAFKA_TOPIC_SMOKE, window_duration="5 minutes", slide_duration="1 minute"):
    """Start Spark streaming with windowed analytics"""
    
    # Create Spark session
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")  # Reduce Spark logging noise
    
    logger.info(f"Starting Spark streaming for topic: {topic}")
    
    # Define schema
    schema = get_sensor_schema()
    
    try:
        # Read from Kafka
        df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .load()
        
        # Parse JSON data and add timestamp
        parsed_df = df.selectExpr("CAST(value AS STRING) as json_data") \
            .select(from_json(col("json_data"), schema).alias("data")) \
            .select("data.*") \
            .withColumn("timestamp", current_timestamp())
        
        # Windowed analytics
        windowed_analytics = parsed_df \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(window(col("timestamp"), window_duration, slide_duration)) \
            .agg(
                avg("Temperature[C]").alias("avg_temperature"),
                avg("Humidity[%]").alias("avg_humidity"),
                avg("TVOC[ppb]").alias("avg_tvoc"),
                avg("eCO2[ppm]").alias("avg_eco2"),
                avg("PM2.5").alias("avg_pm25"),
                avg("Pressure[hPa]").alias("avg_pressure"),
                spark_max("Temperature[C]").alias("max_temperature"),
                spark_min("Temperature[C]").alias("min_temperature"),
                stddev("Temperature[C]").alias("temp_stddev"),
                count("*").alias("record_count"),
                count(when(col("Fire Alarm") == 1, 1)).alias("fire_alarm_count")
            )
        
        # Start streaming query with analytics processing
        analytics_query = windowed_analytics \
            .writeStream \
            .foreachBatch(process_analytics_batch) \
            .outputMode("update") \
            .option("checkpointLocation", "/app/data/checkpoints/analytics") \
            .start()
        
        # Also save raw processed data to CSV for historical record
        save_query = parsed_df \
            .writeStream \
            .format("csv") \
            .option("path", "/app/data/processed_stream") \
            .option("checkpointLocation", "/app/data/checkpoints/raw_data") \
            .option("header", "true") \
            .outputMode("append") \
            .start()
        
        logger.info("Streaming queries started successfully")
        
        # Wait for termination
        analytics_query.awaitTermination()
        save_query.awaitTermination()
        
    except Exception as e:
        logger.error(f"Error in streaming processing: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    start_streaming_analytics()
