from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from batch_processing.tasks.feature_engineering import run_feature_engineering
from batch_processing.tasks.compute_batch_metrics import compute_metrics
# from batch_processing.tasks.train_trigger import trigger_training


default_args = {
    "start_date": datetime(2024, 1, 1),
    "retries": 1
}

with DAG(
    dag_id="smoke_detection_batch_pipeline",
    default_args=default_args,
    schedule_interval=None,
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
