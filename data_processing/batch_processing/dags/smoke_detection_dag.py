import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))  # add /opt/airflow into sys.path


from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from tasks.feature_engineering import run_feature_engineering
from tasks.compute_batch_metrics import compute_metrics
# from batch_processing.tasks.train_trigger import trigger_training


default_args = {
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=3)
}

with DAG(
    dag_id="smoke_detection_batch_pipeline",
    schedule_interval=None,  # trigger by hand
    default_args=default_args,
    catchup=False,
    description="Batch pipeline for smoke detection IoT data"
) as dag:

    t1 = PythonOperator(
        task_id="run_feature_engineering",
        python_callable=run_feature_engineering
    )

    t2 = PythonOperator(
        task_id="compute_batch_metrics",
        python_callable=compute_metrics
    )

    t1 >> [t2]

"""
    t3 = PythonOperator(
        task_id="trigger_training",
        python_callable=trigger_training
    )
"""
    # DAG dependency：first data featuring and then data analysis, last ml training
    # t1 >> [t2, t3]
