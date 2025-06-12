import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from data_processing.batch_processing.tasks.ingest_daily_historical_data import ingest_data
from data_processing.batch_processing.tasks.clean_daily_historical_data import clean_data
from data_processing.batch_processing.tasks.feature_engineering import feature_engineering
from data_processing.batch_processing.tasks.export_processded_results import export_results

default_args = {
    'start_date': datetime(2024, 1, 1),
    'retries': 1
}

with DAG(
    dag_id='daily_data_batch_processing_dag',
    schedule_interval="0 6 * * *",  # Daily at 6 AM
    catchup=False,
    default_args=default_args,
    tags=['smoke', 'batch'],
) as dag:

    ingest = PythonOperator(
        task_id='ingest_daily_historical_data',
        python_callable=ingest_data,
        provide_context=True
    )

    clean = PythonOperator(
        task_id='clean_daily_historical_data',
        python_callable=clean_data,
        provide_context=True
    )

    feature_eng = PythonOperator(
        task_id='feature_engineering',
        python_callable=feature_engineering,
        provide_context=True
    )

    export = PythonOperator(
        task_id='export_peocessded_results',
        python_callable=export_results,
        provide_context=True
    )

    ingest >> clean >> feature_eng >> export
