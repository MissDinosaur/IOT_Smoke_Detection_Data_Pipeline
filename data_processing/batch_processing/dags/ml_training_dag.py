"""
ML Training and Model Management DAG

This DAG handles:
- Automated ML model training
- Model validation and testing
- Model deployment and versioning
- Performance monitoring
- Model rollback if needed

Schedule: Daily at 2 AM
"""

import sys
import os
from pathlib import Path

# Add project paths
sys.path.append("/opt/airflow")
sys.path.append("/opt/airflow/tasks")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import logging

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
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def check_training_data(**context):
    """Check if training data is available and valid."""
    data_path = "/opt/airflow/data/smoke_detection_iot.csv"
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Training data not found: {data_path}")
    
    # Check file size
    file_size = os.path.getsize(data_path)
    if file_size < 1024:  # Less than 1KB
        raise ValueError(f"Training data file too small: {file_size} bytes")
    
    logger.info(f"✅ Training data validated: {data_path} ({file_size} bytes)")
    return data_path

def train_ml_model(**context):
    """Train ML model using the training pipeline."""
    try:
        # Import training modules
        sys.path.append("/opt/airflow/ml/training")
        from ml.training.train_model import train_smoke_detection_model, TrainingConfig
        
        # Configure training
        config = TrainingConfig(
            random_state=42,
            test_size=0.2,
            use_feature_engineering=True
        )
        
        # Get data path from previous task
        data_path = context['task_instance'].xcom_pull(task_ids='check_training_data')
        
        logger.info(f"🤖 Starting ML model training with data: {data_path}")
        
        # Train model
        trainer, results = train_smoke_detection_model(
            data_path=data_path,
            config=config
        )
        
        # Save model with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_dir = Path("/opt/airflow/ml/models")
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = model_dir / f"model_dag_{timestamp}.pkl"
        trainer.save_model(str(model_path))
        
        # Get training results
        best_model_info = results.get("best_model", {})
        
        # Store results in XCom for next tasks
        training_results = {
            "model_path": str(model_path),
            "model_name": best_model_info.get("name", "Unknown"),
            "accuracy": best_model_info.get("accuracy", 0),
            "precision": best_model_info.get("precision", 0),
            "recall": best_model_info.get("recall", 0),
            "f1_score": best_model_info.get("f1", 0),
            "timestamp": timestamp
        }
        
        logger.info(f"✅ Model training completed:")
        logger.info(f"   Model: {training_results['model_name']}")
        logger.info(f"   Accuracy: {training_results['accuracy']:.3f}")
        logger.info(f"   F1-Score: {training_results['f1_score']:.3f}")
        
        return training_results
        
    except Exception as e:
        logger.error(f"❌ Model training failed: {e}")
        raise

def validate_model(**context):
    """Validate the trained model before deployment."""
    try:
        # Get training results from previous task
        training_results = context['task_instance'].xcom_pull(task_ids='train_model')
        
        # Validation thresholds
        min_accuracy = 0.80
        min_f1_score = 0.75
        
        accuracy = training_results["accuracy"]
        f1_score = training_results["f1_score"]
        
        logger.info(f"🔍 Validating model performance:")
        logger.info(f"   Accuracy: {accuracy:.3f} (min: {min_accuracy})")
        logger.info(f"   F1-Score: {f1_score:.3f} (min: {min_f1_score})")
        
        # Check if model meets minimum requirements
        if accuracy < min_accuracy:
            raise ValueError(f"Model accuracy {accuracy:.3f} below threshold {min_accuracy}")
        
        if f1_score < min_f1_score:
            raise ValueError(f"Model F1-score {f1_score:.3f} below threshold {min_f1_score}")
        
        logger.info("✅ Model validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model validation failed: {e}")
        raise

def deploy_model(**context):
    """Deploy the validated model as the production model."""
    try:
        # Get training results
        training_results = context['task_instance'].xcom_pull(task_ids='train_model')
        model_path = training_results["model_path"]
        
        # Copy to production location
        production_model_path = "/opt/airflow/ml/models/best_model.pkl"
        
        import shutil
        shutil.copy2(model_path, production_model_path)
        
        logger.info(f"✅ Model deployed to production: {production_model_path}")
        
        # Log deployment info
        deployment_info = {
            "deployed_at": datetime.now().isoformat(),
            "source_model": model_path,
            "production_model": production_model_path,
            "model_metrics": training_results
        }
        
        return deployment_info
        
    except Exception as e:
        logger.error(f"❌ Model deployment failed: {e}")
        raise

def cleanup_old_models(**context):
    """Clean up old model files, keeping the most recent ones."""
    try:
        model_dir = Path("/opt/airflow/ml/models")
        
        # Get all timestamped model files
        model_files = list(model_dir.glob("model_dag_*.pkl"))
        model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Keep the 5 most recent models
        models_to_keep = 5
        if len(model_files) > models_to_keep:
            for old_model in model_files[models_to_keep:]:
                old_model.unlink()
                logger.info(f"🗑️ Cleaned up old model: {old_model.name}")
        
        logger.info(f"✅ Model cleanup completed. Kept {min(len(model_files), models_to_keep)} models")
        
    except Exception as e:
        logger.warning(f"⚠️ Model cleanup failed: {e}")

def notify_ml_api(**context):
    """Notify ML API service about new model deployment."""
    try:
        import requests
        
        # Get deployment info
        deployment_info = context['task_instance'].xcom_pull(task_ids='deploy_model')
        
        # Notify ML API to reload model
        ml_api_url = "http://ml_api:5000"
        
        # Try to trigger model reload
        try:
            response = requests.post(
                f"{ml_api_url}/model/reload",
                timeout=30
            )
            if response.status_code == 200:
                logger.info("✅ ML API notified of new model deployment")
            else:
                logger.warning(f"⚠️ ML API notification failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Could not reach ML API: {e}")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ ML API notification failed: {e}")

# Define the DAG
with DAG(
    "ml_training_pipeline",
    default_args=default_args,
    description="Automated ML model training and deployment pipeline",
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    catchup=False,
    max_active_runs=1,
    tags=["ml", "training", "model-management"],
) as dag:

    # Task 1: Check if training data is available
    check_data = PythonOperator(
        task_id="check_training_data",
        python_callable=check_training_data,
        doc_md="Check if training data is available and valid"
    )

    # Task 2: Train ML model
    train_model = PythonOperator(
        task_id="train_model",
        python_callable=train_ml_model,
        doc_md="Train ML model using the training pipeline"
    )

    # Task 3: Validate model performance
    validate_model = PythonOperator(
        task_id="validate_model",
        python_callable=validate_model,
        doc_md="Validate model performance against thresholds"
    )

    # Task 4: Deploy model to production
    deploy_model = PythonOperator(
        task_id="deploy_model",
        python_callable=deploy_model,
        doc_md="Deploy validated model to production"
    )

    # Task 5: Clean up old models
    cleanup_models = PythonOperator(
        task_id="cleanup_old_models",
        python_callable=cleanup_old_models,
        doc_md="Clean up old model files"
    )

    # Task 6: Notify ML API service
    notify_api = PythonOperator(
        task_id="notify_ml_api",
        python_callable=notify_ml_api,
        doc_md="Notify ML API service about new model"
    )

    # Define task dependencies
    check_data >> train_model >> validate_model >> deploy_model >> [cleanup_models, notify_api]
