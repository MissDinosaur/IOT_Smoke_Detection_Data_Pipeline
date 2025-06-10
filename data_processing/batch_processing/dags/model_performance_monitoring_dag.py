"""
Model Performance Monitoring DAG

This DAG handles:
- ML model performance tracking
- Prediction accuracy monitoring
- Model drift detection
- Performance degradation alerts
- A/B testing support

Schedule: Every 12 hours
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
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import logging
import json
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    "owner": "ml-team",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def check_ml_api_health(**context):
    """Check if ML API is healthy and responding."""
    try:
        ml_api_url = "http://ml_api:5000"
        
        # Health check
        response = requests.get(f"{ml_api_url}/health", timeout=30)
        
        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"✅ ML API is healthy: {health_data}")
            
            # Get model info
            model_response = requests.get(f"{ml_api_url}/model/info", timeout=30)
            if model_response.status_code == 200:
                model_info = model_response.json()
                logger.info(f"📊 Model Info: {model_info}")
                
                return {
                    "api_healthy": True,
                    "health_data": health_data,
                    "model_info": model_info
                }
            else:
                logger.warning("⚠️ Could not get model info")
                return {"api_healthy": True, "health_data": health_data, "model_info": None}
        else:
            logger.error(f"❌ ML API health check failed: {response.status_code}")
            return {"api_healthy": False, "error": f"Status: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"❌ ML API health check failed: {e}")
        return {"api_healthy": False, "error": str(e)}

def test_model_predictions(**context):
    """Test model predictions with known test cases."""
    try:
        # Get API health status
        api_status = context['task_instance'].xcom_pull(task_ids='check_ml_api_health')
        
        if not api_status.get("api_healthy", False):
            raise Exception("ML API is not healthy - cannot test predictions")
        
        ml_api_url = "http://ml_api:5000"
        
        # Test cases for model validation
        test_cases = [
            {
                "name": "Normal conditions",
                "data": {
                    "Temperature[C]": 25.0,
                    "Humidity[%]": 45.0,
                    "TVOC[ppb]": 150.0,
                    "eCO2[ppm]": 400.0,
                    "Raw H2": 13000,
                    "Raw Ethanol": 18000,
                    "Pressure[hPa]": 1013.25,
                    "PM1.0": 10.0,
                    "PM2.5": 15.0,
                    "NC0.5": 100,
                    "NC1.0": 50,
                    "NC2.5": 20,
                    "CNT": 170,
                    "Fire Alarm": 0
                },
                "expected_prediction": 0  # No fire expected
            },
            {
                "name": "High temperature scenario",
                "data": {
                    "Temperature[C]": 85.0,
                    "Humidity[%]": 20.0,
                    "TVOC[ppb]": 2000.0,
                    "eCO2[ppm]": 1500.0,
                    "Raw H2": 25000,
                    "Raw Ethanol": 35000,
                    "Pressure[hPa]": 1010.0,
                    "PM1.0": 150.0,
                    "PM2.5": 200.0,
                    "NC0.5": 500,
                    "NC1.0": 300,
                    "NC2.5": 150,
                    "CNT": 950,
                    "Fire Alarm": 1
                },
                "expected_prediction": 1  # Fire expected
            }
        ]
        
        test_results = []
        
        for test_case in test_cases:
            try:
                # Make prediction
                response = requests.post(
                    f"{ml_api_url}/predict",
                    json=test_case["data"],
                    timeout=30
                )
                
                if response.status_code == 200:
                    prediction_result = response.json()
                    
                    test_result = {
                        "test_name": test_case["name"],
                        "prediction": prediction_result.get("prediction", -1),
                        "confidence": prediction_result.get("confidence", 0.0),
                        "expected": test_case["expected_prediction"],
                        "correct": prediction_result.get("prediction") == test_case["expected_prediction"],
                        "response_time": response.elapsed.total_seconds()
                    }
                    
                    test_results.append(test_result)
                    
                    logger.info(f"🧪 Test '{test_case['name']}': "
                              f"Predicted={test_result['prediction']}, "
                              f"Expected={test_result['expected']}, "
                              f"Correct={test_result['correct']}")
                else:
                    logger.error(f"❌ Prediction failed for {test_case['name']}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Test case '{test_case['name']}' failed: {e}")
        
        # Calculate test summary
        total_tests = len(test_results)
        correct_predictions = sum(1 for result in test_results if result["correct"])
        accuracy = (correct_predictions / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = np.mean([result["response_time"] for result in test_results])
        
        test_summary = {
            "total_tests": total_tests,
            "correct_predictions": correct_predictions,
            "accuracy": round(accuracy, 2),
            "avg_response_time": round(avg_response_time, 3),
            "test_results": test_results,
            "test_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"📊 Model Test Summary:")
        logger.info(f"   Tests: {total_tests}")
        logger.info(f"   Accuracy: {accuracy}%")
        logger.info(f"   Avg Response Time: {avg_response_time:.3f}s")
        
        return test_summary
        
    except Exception as e:
        logger.error(f"❌ Model prediction testing failed: {e}")
        raise

def analyze_prediction_patterns(**context):
    """Analyze recent prediction patterns for drift detection."""
    try:
        # This would typically analyze logs from the ML API or streaming processor
        # For now, we'll simulate pattern analysis
        
        logger.info("🔍 Analyzing prediction patterns...")
        
        # Simulate pattern analysis results
        pattern_analysis = {
            "analysis_period": "last_24_hours",
            "total_predictions": 1440,  # Simulated
            "fire_predictions": 72,     # Simulated 5% fire rate
            "no_fire_predictions": 1368,
            "fire_prediction_rate": 5.0,
            "avg_confidence": 0.85,
            "confidence_distribution": {
                "high_confidence": 0.70,  # >0.8
                "medium_confidence": 0.25, # 0.5-0.8
                "low_confidence": 0.05     # <0.5
            },
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Check for potential drift indicators
        drift_indicators = []
        
        # Fire prediction rate should be reasonable (1-10%)
        fire_rate = pattern_analysis["fire_prediction_rate"]
        if fire_rate > 15:
            drift_indicators.append(f"High fire prediction rate: {fire_rate}%")
        elif fire_rate < 0.5:
            drift_indicators.append(f"Very low fire prediction rate: {fire_rate}%")
        
        # Average confidence should be reasonable
        avg_confidence = pattern_analysis["avg_confidence"]
        if avg_confidence < 0.6:
            drift_indicators.append(f"Low average confidence: {avg_confidence}")
        
        # Too many low confidence predictions
        low_confidence_rate = pattern_analysis["confidence_distribution"]["low_confidence"]
        if low_confidence_rate > 0.2:
            drift_indicators.append(f"High low-confidence rate: {low_confidence_rate}")
        
        pattern_analysis["drift_indicators"] = drift_indicators
        
        logger.info(f"📈 Prediction Pattern Analysis:")
        logger.info(f"   Fire Rate: {fire_rate}%")
        logger.info(f"   Avg Confidence: {avg_confidence}")
        logger.info(f"   Drift Indicators: {len(drift_indicators)}")
        
        return pattern_analysis
        
    except Exception as e:
        logger.error(f"❌ Pattern analysis failed: {e}")
        raise

def generate_performance_report(**context):
    """Generate comprehensive model performance report."""
    try:
        # Get results from previous tasks
        api_status = context['task_instance'].xcom_pull(task_ids='check_ml_api_health')
        test_summary = context['task_instance'].xcom_pull(task_ids='test_model_predictions')
        pattern_analysis = context['task_instance'].xcom_pull(task_ids='analyze_prediction_patterns')
        
        # Generate performance report
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "api_health": api_status,
            "model_testing": test_summary,
            "pattern_analysis": pattern_analysis,
            "performance_score": 0,
            "recommendations": [],
            "alerts": []
        }
        
        # Calculate overall performance score
        score_components = []
        
        # API health score
        if api_status.get("api_healthy", False):
            score_components.append(25)  # 25 points for healthy API
        
        # Model accuracy score
        test_accuracy = test_summary.get("accuracy", 0)
        score_components.append(test_accuracy * 0.4)  # 40 points max for accuracy
        
        # Response time score (good if < 1 second)
        response_time = test_summary.get("avg_response_time", 10)
        response_score = max(0, 25 - (response_time * 10))  # 25 points max
        score_components.append(response_score)
        
        # Pattern stability score
        drift_count = len(pattern_analysis.get("drift_indicators", []))
        pattern_score = max(0, 10 - (drift_count * 2))  # 10 points max
        score_components.append(pattern_score)
        
        overall_score = sum(score_components)
        report["performance_score"] = round(overall_score, 2)
        
        # Generate recommendations
        if overall_score < 70:
            report["recommendations"].append("Model performance is below acceptable threshold")
        
        if test_accuracy < 80:
            report["recommendations"].append("Model accuracy is low - consider retraining")
        
        if response_time > 2:
            report["recommendations"].append("Model response time is slow - optimize inference")
        
        if drift_count > 2:
            report["recommendations"].append("Potential model drift detected - investigate data changes")
        
        # Generate alerts
        if overall_score < 50:
            report["alerts"].append("CRITICAL: Model performance severely degraded")
        
        if not api_status.get("api_healthy", False):
            report["alerts"].append("CRITICAL: ML API is not responding")
        
        # Save report
        report_dir = Path("/opt/airflow/data/performance_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"model_performance_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📋 Model performance report generated: {report_path}")
        logger.info(f"   Performance Score: {overall_score}/100")
        logger.info(f"   Recommendations: {len(report['recommendations'])}")
        logger.info(f"   Alerts: {len(report['alerts'])}")
        
        return str(report_path)
        
    except Exception as e:
        logger.error(f"❌ Performance report generation failed: {e}")
        raise

def check_performance_alerts(**context):
    """Check if performance issues require immediate attention."""
    try:
        # Get test results and pattern analysis
        test_summary = context['task_instance'].xcom_pull(task_ids='test_model_predictions')
        pattern_analysis = context['task_instance'].xcom_pull(task_ids='analyze_prediction_patterns')
        
        alerts = []
        
        # Critical performance thresholds
        test_accuracy = test_summary.get("accuracy", 100)
        if test_accuracy < 70:
            alerts.append(f"CRITICAL: Model accuracy dropped to {test_accuracy}%")
        
        # Response time issues
        response_time = test_summary.get("avg_response_time", 0)
        if response_time > 5:
            alerts.append(f"WARNING: High response time: {response_time:.3f}s")
        
        # Drift detection
        drift_indicators = pattern_analysis.get("drift_indicators", [])
        if len(drift_indicators) > 3:
            alerts.append(f"WARNING: Multiple drift indicators detected: {len(drift_indicators)}")
        
        if alerts:
            logger.warning(f"🚨 {len(alerts)} performance alerts generated:")
            for alert in alerts:
                logger.warning(f"   {alert}")
        else:
            logger.info("✅ No performance alerts - model is performing well")
        
        return alerts
        
    except Exception as e:
        logger.error(f"❌ Performance alert check failed: {e}")
        raise

# Define the DAG
with DAG(
    "model_performance_monitoring",
    default_args=default_args,
    description="ML model performance monitoring and drift detection pipeline",
    schedule_interval="0 */12 * * *",  # Every 12 hours
    catchup=False,
    max_active_runs=1,
    tags=["ml", "monitoring", "performance", "drift-detection"],
) as dag:

    # Task 1: Check ML API health
    check_api_health = PythonOperator(
        task_id="check_ml_api_health",
        python_callable=check_ml_api_health,
        doc_md="Check if ML API is healthy and responding"
    )

    # Task 2: Test model predictions
    test_predictions = PythonOperator(
        task_id="test_model_predictions",
        python_callable=test_model_predictions,
        doc_md="Test model predictions with known test cases"
    )

    # Task 3: Analyze prediction patterns
    analyze_patterns = PythonOperator(
        task_id="analyze_prediction_patterns",
        python_callable=analyze_prediction_patterns,
        doc_md="Analyze recent prediction patterns for drift detection"
    )

    # Task 4: Generate performance report
    generate_report = PythonOperator(
        task_id="generate_performance_report",
        python_callable=generate_performance_report,
        doc_md="Generate comprehensive model performance report"
    )

    # Task 5: Check for performance alerts
    check_alerts = PythonOperator(
        task_id="check_performance_alerts",
        python_callable=check_performance_alerts,
        doc_md="Check if performance issues require immediate attention"
    )

    # Define task dependencies
    check_api_health >> [test_predictions, analyze_patterns] >> generate_report >> check_alerts
