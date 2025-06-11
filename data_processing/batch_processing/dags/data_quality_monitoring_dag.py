"""
Data Quality Monitoring DAG

This DAG handles:
- Data quality checks on streaming data
- Anomaly detection in sensor readings
- Data completeness validation
- Alert generation for data quality issues
- Historical data quality reporting

Schedule: Every 6 hours
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add project paths
sys.path.append("/opt/airflow")
sys.path.append("/opt/airflow/tasks")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

def check_data_availability(**context):
    """Check if recent data is available for quality analysis."""
    data_paths = [
        "/opt/airflow/data/smoke_detection_iot.csv",
        "/opt/airflow/data/processed_stream"
    ]
    
    available_data = []
    
    for path in data_paths:
        if os.path.exists(path):
            if os.path.isfile(path):
                size = os.path.getsize(path)
                available_data.append({"path": path, "type": "file", "size": size})
            elif os.path.isdir(path):
                files = list(Path(path).glob("*.csv"))
                available_data.append({"path": path, "type": "directory", "files": len(files)})
    
    if not available_data:
        raise FileNotFoundError("No data available for quality analysis")
    
    logger.info(f"✅ Found {len(available_data)} data sources for quality analysis")
    return available_data

def analyze_data_quality(**context):
    """Perform comprehensive data quality analysis."""
    try:
        # Load main dataset
        data_path = "/opt/airflow/data/smoke_detection_iot.csv"
        df = pd.read_csv(data_path)
        
        logger.info(f"📊 Analyzing data quality for {len(df)} records")
        
        # Data quality metrics
        quality_metrics = {}
        
        # 1. Completeness check
        missing_data = df.isnull().sum()
        completeness = ((len(df) - missing_data) / len(df) * 100).round(2)
        quality_metrics["completeness"] = completeness.to_dict()
        
        # 2. Data type validation
        expected_numeric_cols = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5"
        ]
        
        type_issues = []
        for col in expected_numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    type_issues.append(col)
        
        quality_metrics["type_issues"] = type_issues
        
        # 3. Range validation
        range_issues = []
        
        # Temperature should be reasonable (-50 to 100°C)
        if "Temperature[C]" in df.columns:
            temp_outliers = df[(df["Temperature[C]"] < -50) | (df["Temperature[C]"] > 100)]
            if len(temp_outliers) > 0:
                range_issues.append(f"Temperature outliers: {len(temp_outliers)} records")
        
        # Humidity should be 0-100%
        if "Humidity[%]" in df.columns:
            humidity_outliers = df[(df["Humidity[%]"] < 0) | (df["Humidity[%]"] > 100)]
            if len(humidity_outliers) > 0:
                range_issues.append(f"Humidity outliers: {len(humidity_outliers)} records")
        
        quality_metrics["range_issues"] = range_issues
        
        # 4. Duplicate detection
        duplicates = df.duplicated().sum()
        quality_metrics["duplicates"] = int(duplicates)
        
        # 5. Statistical anomalies
        anomalies = {}
        for col in expected_numeric_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                anomalies[col] = len(outliers)
        
        quality_metrics["statistical_anomalies"] = anomalies
        
        # 6. Overall quality score
        completeness_score = completeness.mean()
        type_score = 100 - (len(type_issues) / len(expected_numeric_cols) * 100)
        range_score = 100 - (len(range_issues) * 10)  # Each issue reduces score by 10
        duplicate_score = 100 - (duplicates / len(df) * 100)
        
        overall_score = (completeness_score + type_score + range_score + duplicate_score) / 4
        quality_metrics["overall_quality_score"] = round(overall_score, 2)
        
        logger.info(f"📈 Data Quality Analysis Results:")
        logger.info(f"   Overall Score: {overall_score:.2f}%")
        logger.info(f"   Completeness: {completeness_score:.2f}%")
        logger.info(f"   Type Issues: {len(type_issues)}")
        logger.info(f"   Range Issues: {len(range_issues)}")
        logger.info(f"   Duplicates: {duplicates}")
        
        return quality_metrics
        
    except Exception as e:
        logger.error(f"❌ Data quality analysis failed: {e}")
        raise

def detect_anomalies(**context):
    """Detect anomalies in recent sensor data."""
    try:
        # Load data
        data_path = "/opt/airflow/data/smoke_detection_iot.csv"
        df = pd.read_csv(data_path)
        
        # Focus on recent data (last 1000 records)
        recent_df = df.tail(1000)
        
        logger.info(f"🔍 Detecting anomalies in {len(recent_df)} recent records")
        
        anomaly_results = {}
        
        # Sensor-specific anomaly detection
        sensor_thresholds = {
            "Temperature[C]": {"min": -10, "max": 60, "std_multiplier": 3},
            "Humidity[%]": {"min": 0, "max": 100, "std_multiplier": 3},
            "TVOC[ppb]": {"min": 0, "max": 5000, "std_multiplier": 3},
            "PM2.5": {"min": 0, "max": 500, "std_multiplier": 3}
        }
        
        for sensor, thresholds in sensor_thresholds.items():
            if sensor in recent_df.columns:
                sensor_data = recent_df[sensor].dropna()
                
                # Range-based anomalies
                range_anomalies = sensor_data[
                    (sensor_data < thresholds["min"]) | 
                    (sensor_data > thresholds["max"])
                ]
                
                # Statistical anomalies (Z-score method)
                mean_val = sensor_data.mean()
                std_val = sensor_data.std()
                z_scores = np.abs((sensor_data - mean_val) / std_val)
                statistical_anomalies = sensor_data[z_scores > thresholds["std_multiplier"]]
                
                anomaly_results[sensor] = {
                    "range_anomalies": len(range_anomalies),
                    "statistical_anomalies": len(statistical_anomalies),
                    "total_anomalies": len(range_anomalies) + len(statistical_anomalies)
                }
        
        # Calculate anomaly rate
        total_anomalies = sum(result["total_anomalies"] for result in anomaly_results.values())
        anomaly_rate = (total_anomalies / (len(recent_df) * len(anomaly_results))) * 100
        
        anomaly_summary = {
            "anomaly_results": anomaly_results,
            "total_anomalies": total_anomalies,
            "anomaly_rate": round(anomaly_rate, 2),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🚨 Anomaly Detection Results:")
        logger.info(f"   Total Anomalies: {total_anomalies}")
        logger.info(f"   Anomaly Rate: {anomaly_rate:.2f}%")
        
        return anomaly_summary
        
    except Exception as e:
        logger.error(f"❌ Anomaly detection failed: {e}")
        raise

def generate_quality_report(**context):
    """Generate comprehensive data quality report."""
    try:
        # Get results from previous tasks
        quality_metrics = context['task_instance'].xcom_pull(task_ids='analyze_data_quality')
        anomaly_summary = context['task_instance'].xcom_pull(task_ids='detect_anomalies')
        
        # Generate report
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "data_quality_metrics": quality_metrics,
            "anomaly_detection": anomaly_summary,
            "recommendations": []
        }
        
        # Generate recommendations based on findings
        overall_score = quality_metrics.get("overall_quality_score", 0)
        
        if overall_score < 80:
            report["recommendations"].append("Data quality score is below 80%. Investigate data sources.")
        
        if quality_metrics.get("duplicates", 0) > 100:
            report["recommendations"].append("High number of duplicate records detected. Review data ingestion process.")
        
        if len(quality_metrics.get("type_issues", [])) > 0:
            report["recommendations"].append("Data type issues detected. Validate data parsing and transformation.")
        
        if anomaly_summary.get("anomaly_rate", 0) > 5:
            report["recommendations"].append("High anomaly rate detected. Check sensor calibration and data collection.")
        
        # Save report
        report_dir = Path("/opt/airflow/data/quality_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"data_quality_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📋 Data quality report generated: {report_path}")
        logger.info(f"   Overall Quality Score: {overall_score}%")
        logger.info(f"   Recommendations: {len(report['recommendations'])}")
        
        return str(report_path)
        
    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")
        raise

def check_quality_alerts(**context):
    """Check if quality issues require immediate attention."""
    try:
        # Get quality metrics
        quality_metrics = context['task_instance'].xcom_pull(task_ids='analyze_data_quality')
        anomaly_summary = context['task_instance'].xcom_pull(task_ids='detect_anomalies')
        
        alerts = []
        
        # Critical quality thresholds
        overall_score = quality_metrics.get("overall_quality_score", 100)
        if overall_score < 70:
            alerts.append(f"CRITICAL: Data quality score dropped to {overall_score}%")
        
        # High anomaly rate
        anomaly_rate = anomaly_summary.get("anomaly_rate", 0)
        if anomaly_rate > 10:
            alerts.append(f"WARNING: High anomaly rate detected: {anomaly_rate}%")
        
        # Missing data issues
        completeness = quality_metrics.get("completeness", {})
        for column, score in completeness.items():
            if score < 90:
                alerts.append(f"WARNING: {column} completeness below 90%: {score}%")
        
        if alerts:
            logger.warning(f"🚨 {len(alerts)} quality alerts generated:")
            for alert in alerts:
                logger.warning(f"   {alert}")
        else:
            logger.info("✅ No quality alerts - data quality is acceptable")
        
        return alerts
        
    except Exception as e:
        logger.error(f"❌ Quality alert check failed: {e}")
        raise

# Define the DAG
with DAG(
    "data_quality_monitoring",
    default_args=default_args,
    description="Data quality monitoring and anomaly detection pipeline",
    schedule_interval="0 */6 * * *",  # Every 6 hours
    catchup=False,
    max_active_runs=1,
    tags=["data-quality", "monitoring", "anomaly-detection"],
) as dag:

    # Task 1: Check data availability
    check_data = PythonOperator(
        task_id="check_data_availability",
        python_callable=check_data_availability,
        doc_md="Check if data is available for quality analysis"
    )

    # Task 2: Analyze data quality
    analyze_quality = PythonOperator(
        task_id="analyze_data_quality",
        python_callable=analyze_data_quality,
        doc_md="Perform comprehensive data quality analysis"
    )

    # Task 3: Detect anomalies
    detect_anomalies = PythonOperator(
        task_id="detect_anomalies",
        python_callable=detect_anomalies,
        doc_md="Detect anomalies in sensor data"
    )

    # Task 4: Generate quality report
    generate_report = PythonOperator(
        task_id="generate_quality_report",
        python_callable=generate_quality_report,
        doc_md="Generate comprehensive data quality report"
    )

    # Task 5: Check for quality alerts
    check_alerts = PythonOperator(
        task_id="check_quality_alerts",
        python_callable=check_quality_alerts,
        doc_md="Check if quality issues require immediate attention"
    )

    # Define task dependencies
    check_data >> [analyze_quality, detect_anomalies] >> generate_report >> check_alerts
