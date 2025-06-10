"""
Historical Data Processing DAG

This DAG handles:
- Processing historical sensor data with ML models
- Generating insights from historical patterns
- Creating training datasets for model improvement
- Performance analysis on historical data
- Data archival and cleanup

Schedule: Weekly on Sundays at 3 AM
"""

import sys
import os
from pathlib import Path
import pandas as pd

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
    "retry_delay": timedelta(minutes=10),
}

def discover_historical_data(**context):
    """Discover available historical data files."""
    try:
        data_directories = [
            "/opt/airflow/data",
            "/opt/airflow/data/processed_stream",
            "/opt/airflow/data/historical"
        ]
        
        discovered_files = []
        
        for data_dir in data_directories:
            if os.path.exists(data_dir):
                data_path = Path(data_dir)
                
                # Find CSV files
                csv_files = list(data_path.glob("**/*.csv"))
                
                for csv_file in csv_files:
                    file_info = {
                        "path": str(csv_file),
                        "size": csv_file.stat().st_size,
                        "modified": csv_file.stat().st_mtime,
                        "name": csv_file.name
                    }
                    discovered_files.append(file_info)
        
        # Sort by modification time (newest first)
        discovered_files.sort(key=lambda x: x["modified"], reverse=True)
        
        logger.info(f"📁 Discovered {len(discovered_files)} historical data files")
        for file_info in discovered_files[:5]:  # Log first 5 files
            size_mb = file_info["size"] / (1024 * 1024)
            logger.info(f"   {file_info['name']}: {size_mb:.2f} MB")
        
        return discovered_files
        
    except Exception as e:
        logger.error(f"❌ Historical data discovery failed: {e}")
        raise

def process_historical_with_ml(**context):
    """Process historical data using ML models."""
    try:
        # Get discovered files
        discovered_files = context['task_instance'].xcom_pull(task_ids='discover_historical_data')
        
        if not discovered_files:
            logger.warning("⚠️ No historical data files found")
            return {"processed_files": 0, "total_predictions": 0}
        
        # Use the main dataset for processing
        main_dataset = None
        for file_info in discovered_files:
            if "smoke_detection_iot.csv" in file_info["name"]:
                main_dataset = file_info["path"]
                break
        
        if not main_dataset:
            main_dataset = discovered_files[0]["path"]  # Use first available file
        
        logger.info(f"🤖 Processing historical data with ML: {main_dataset}")
        
        # Import historical ML processor
        sys.path.append("/opt/airflow/data_processing/stream_processing")
        from historical_ml_processor import HistoricalMLProcessor
        
        # Initialize processor
        processor = HistoricalMLProcessor(
            model_path="/opt/airflow/ml/models/best_model.pkl",
            batch_size=1000
        )
        
        # Initialize ML model
        if not processor.initialize_ml_model():
            logger.warning("⚠️ ML model not available - processing without ML predictions")
            return {"processed_files": 0, "total_predictions": 0, "ml_available": False}
        
        # Process the dataset
        results = processor.process_historical_file(
            input_path=main_dataset,
            output_path="/opt/airflow/data/historical_ml_results"
        )
        
        # Extract key metrics
        summary = results.get("summary", {})
        performance_metrics = results.get("performance_metrics", {})
        
        processing_results = {
            "processed_files": 1,
            "total_records": summary.get("total_records", 0),
            "total_predictions": summary.get("successful_predictions", 0),
            "fire_predictions": summary.get("fire_predictions", 0),
            "fire_rate": summary.get("fire_prediction_rate", 0),
            "processing_time": summary.get("processing_time", 0),
            "ml_available": True,
            "model_performance": performance_metrics
        }
        
        logger.info(f"✅ Historical ML processing completed:")
        logger.info(f"   Records Processed: {processing_results['total_records']}")
        logger.info(f"   ML Predictions: {processing_results['total_predictions']}")
        logger.info(f"   Fire Rate: {processing_results['fire_rate']:.2%}")
        
        return processing_results
        
    except Exception as e:
        logger.error(f"❌ Historical ML processing failed: {e}")
        # Return partial results to continue pipeline
        return {"processed_files": 0, "total_predictions": 0, "ml_available": False, "error": str(e)}

def analyze_historical_patterns(**context):
    """Analyze patterns in historical data."""
    try:
        # Get processing results
        ml_results = context['task_instance'].xcom_pull(task_ids='process_historical_with_ml')
        
        # Load main dataset for pattern analysis
        data_path = "/opt/airflow/data/smoke_detection_iot.csv"
        df = pd.read_csv(data_path)
        
        logger.info(f"📊 Analyzing patterns in {len(df)} historical records")
        
        # Temporal patterns
        if 'UTC' in df.columns:
            df['UTC'] = pd.to_datetime(df['UTC'])
            df['hour'] = df['UTC'].dt.hour
            df['day_of_week'] = df['UTC'].dt.dayofweek
            
            # Fire alarm patterns by time
            hourly_fire_rate = df.groupby('hour')['Fire Alarm'].mean()
            daily_fire_rate = df.groupby('day_of_week')['Fire Alarm'].mean()
            
            peak_fire_hour = hourly_fire_rate.idxmax()
            peak_fire_day = daily_fire_rate.idxmax()
        else:
            peak_fire_hour = None
            peak_fire_day = None
        
        # Sensor correlation patterns
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        correlation_matrix = df[numeric_columns].corr()
        
        # Find strongest correlations with Fire Alarm
        if 'Fire Alarm' in correlation_matrix.columns:
            fire_correlations = correlation_matrix['Fire Alarm'].abs().sort_values(ascending=False)
            top_fire_indicators = fire_correlations.head(5).to_dict()
        else:
            top_fire_indicators = {}
        
        # Environmental patterns
        temp_stats = df['Temperature[C]'].describe() if 'Temperature[C]' in df.columns else {}
        humidity_stats = df['Humidity[%]'].describe() if 'Humidity[%]' in df.columns else {}
        tvoc_stats = df['TVOC[ppb]'].describe() if 'TVOC[ppb]' in df.columns else {}
        
        pattern_analysis = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_records_analyzed": len(df),
            "temporal_patterns": {
                "peak_fire_hour": int(peak_fire_hour) if peak_fire_hour is not None else None,
                "peak_fire_day": int(peak_fire_day) if peak_fire_day is not None else None
            },
            "fire_indicators": top_fire_indicators,
            "environmental_stats": {
                "temperature": temp_stats.to_dict() if not temp_stats.empty else {},
                "humidity": humidity_stats.to_dict() if not humidity_stats.empty else {},
                "tvoc": tvoc_stats.to_dict() if not tvoc_stats.empty else {}
            },
            "ml_processing_results": ml_results
        }
        
        logger.info(f"📈 Historical Pattern Analysis:")
        if peak_fire_hour is not None:
            logger.info(f"   Peak Fire Hour: {peak_fire_hour}:00")
        if peak_fire_day is not None:
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            logger.info(f"   Peak Fire Day: {days[peak_fire_day]}")
        logger.info(f"   Top Fire Indicators: {list(top_fire_indicators.keys())[:3]}")
        
        return pattern_analysis
        
    except Exception as e:
        logger.error(f"❌ Historical pattern analysis failed: {e}")
        raise

def generate_insights_report(**context):
    """Generate insights report from historical analysis."""
    try:
        # Get pattern analysis results
        pattern_analysis = context['task_instance'].xcom_pull(task_ids='analyze_historical_patterns')
        
        # Generate insights
        insights = []
        recommendations = []
        
        # Temporal insights
        temporal_patterns = pattern_analysis.get("temporal_patterns", {})
        peak_hour = temporal_patterns.get("peak_fire_hour")
        peak_day = temporal_patterns.get("peak_fire_day")
        
        if peak_hour is not None:
            insights.append(f"Fire incidents peak at {peak_hour}:00 hours")
            recommendations.append(f"Increase monitoring during {peak_hour}:00-{(peak_hour+1)%24}:00 hours")
        
        if peak_day is not None:
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            insights.append(f"Fire incidents are highest on {days[peak_day]}s")
            recommendations.append(f"Enhanced monitoring recommended on {days[peak_day]}s")
        
        # Sensor insights
        fire_indicators = pattern_analysis.get("fire_indicators", {})
        if fire_indicators:
            top_indicator = list(fire_indicators.keys())[0]
            correlation = fire_indicators[top_indicator]
            insights.append(f"{top_indicator} shows strongest correlation with fire events ({correlation:.3f})")
            recommendations.append(f"Prioritize {top_indicator} monitoring for early fire detection")
        
        # Environmental insights
        env_stats = pattern_analysis.get("environmental_stats", {})
        temp_stats = env_stats.get("temperature", {})
        if temp_stats and "mean" in temp_stats:
            avg_temp = temp_stats["mean"]
            max_temp = temp_stats["max"]
            insights.append(f"Average temperature: {avg_temp:.1f}°C, Maximum: {max_temp:.1f}°C")
            
            if max_temp > 80:
                recommendations.append("High temperature readings detected - verify sensor calibration")
        
        # ML performance insights
        ml_results = pattern_analysis.get("ml_processing_results", {})
        if ml_results.get("ml_available", False):
            fire_rate = ml_results.get("fire_rate", 0)
            model_performance = ml_results.get("model_performance", {})
            
            insights.append(f"ML model detected fire conditions in {fire_rate:.2%} of historical data")
            
            if "accuracy" in model_performance:
                accuracy = model_performance["accuracy"]
                insights.append(f"ML model historical accuracy: {accuracy:.1%}")
                
                if accuracy < 0.85:
                    recommendations.append("Model accuracy below 85% - consider retraining with more data")
        
        # Generate comprehensive report
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "report_type": "historical_insights",
            "analysis_period": "full_historical_dataset",
            "pattern_analysis": pattern_analysis,
            "insights": insights,
            "recommendations": recommendations,
            "data_summary": {
                "total_records": pattern_analysis.get("total_records_analyzed", 0),
                "ml_predictions": ml_results.get("total_predictions", 0),
                "processing_time": ml_results.get("processing_time", 0)
            }
        }
        
        # Save report
        report_dir = Path("/opt/airflow/data/insights_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"historical_insights_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📋 Historical insights report generated: {report_path}")
        logger.info(f"   Insights: {len(insights)}")
        logger.info(f"   Recommendations: {len(recommendations)}")
        
        return str(report_path)
        
    except Exception as e:
        logger.error(f"❌ Insights report generation failed: {e}")
        raise

def cleanup_old_reports(**context):
    """Clean up old report files to save storage space."""
    try:
        report_directories = [
            "/opt/airflow/data/historical_ml_results",
            "/opt/airflow/data/insights_reports",
            "/opt/airflow/data/quality_reports",
            "/opt/airflow/data/performance_reports"
        ]
        
        cleanup_summary = {"directories_cleaned": 0, "files_removed": 0, "space_freed": 0}
        
        # Keep files from last 30 days
        cutoff_time = datetime.now() - timedelta(days=30)
        cutoff_timestamp = cutoff_time.timestamp()
        
        for report_dir in report_directories:
            if os.path.exists(report_dir):
                report_path = Path(report_dir)
                old_files = []
                
                for file_path in report_path.glob("**/*"):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_timestamp:
                        old_files.append(file_path)
                
                # Remove old files
                for old_file in old_files:
                    file_size = old_file.stat().st_size
                    old_file.unlink()
                    cleanup_summary["files_removed"] += 1
                    cleanup_summary["space_freed"] += file_size
                
                if old_files:
                    cleanup_summary["directories_cleaned"] += 1
                    logger.info(f"🗑️ Cleaned {len(old_files)} old files from {report_dir}")
        
        space_freed_mb = cleanup_summary["space_freed"] / (1024 * 1024)
        logger.info(f"✅ Cleanup completed:")
        logger.info(f"   Directories: {cleanup_summary['directories_cleaned']}")
        logger.info(f"   Files Removed: {cleanup_summary['files_removed']}")
        logger.info(f"   Space Freed: {space_freed_mb:.2f} MB")
        
        return cleanup_summary
        
    except Exception as e:
        logger.warning(f"⚠️ Cleanup failed: {e}")
        return {"error": str(e)}

# Define the DAG
with DAG(
    "historical_data_processing",
    default_args=default_args,
    description="Historical data processing and insights generation pipeline",
    schedule_interval="0 3 * * 0",  # Weekly on Sundays at 3 AM
    catchup=False,
    max_active_runs=1,
    tags=["historical", "ml", "insights", "analysis"],
) as dag:

    # Task 1: Discover historical data files
    discover_data = PythonOperator(
        task_id="discover_historical_data",
        python_callable=discover_historical_data,
        doc_md="Discover available historical data files"
    )

    # Task 2: Process historical data with ML
    process_with_ml = PythonOperator(
        task_id="process_historical_with_ml",
        python_callable=process_historical_with_ml,
        doc_md="Process historical data using ML models"
    )

    # Task 3: Analyze historical patterns
    analyze_patterns = PythonOperator(
        task_id="analyze_historical_patterns",
        python_callable=analyze_historical_patterns,
        doc_md="Analyze patterns in historical data"
    )

    # Task 4: Generate insights report
    generate_insights = PythonOperator(
        task_id="generate_insights_report",
        python_callable=generate_insights_report,
        doc_md="Generate insights report from historical analysis"
    )

    # Task 5: Clean up old reports
    cleanup_reports = PythonOperator(
        task_id="cleanup_old_reports",
        python_callable=cleanup_old_reports,
        doc_md="Clean up old report files to save storage space"
    )

    # Define task dependencies
    discover_data >> process_with_ml >> analyze_patterns >> generate_insights >> cleanup_reports
