import sys
import os

sys.path.append(
    os.path.abspath(os.path.dirname(__file__) + "/..")
)  # add /opt/airflow into sys.path

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import os
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import HISTORICAL_DATA_FILE_PREFIX

today = datetime.now()
# Calculate yesterday's date by subtracting 1 day from today
yesterday = today - timedelta(days=1)
# Get only the date part (year-month-day) without time
yesterday_date = yesterday.date()
# Format the date as a string in YYYY-MM-DD format
yesterday_str = yesterday_date.strftime("%Y-%m-%d")

# The csv filename contains the execution date, e.g. 'historical_data_2025-06-12.csv'
HISTORICAL_DATA_FILE_NAME = HISTORICAL_DATA_FILE_PREFIX+"_"+yesterday_str+".csv"
# Path to historical data file
DATA_FILE_FROM_PREVIOUS_DAY = build_relative_path(DATA_DIR, HISTORICAL_DATA_FILE_NAME)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def aggregate_daily_data(**kwargs):
    filename = DATA_FILE_FROM_PREVIOUS_DAY
    
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist.")
    
    df = pd.read_csv(filename)

    # Convert UTC to datetime for reference (optional)
    df['datetime'] = pd.to_datetime(df['UTC'], unit='s')
    # Exclude non-numeric columns that don't make sense to aggregate
    exclude_cols = ['UTC', 'datetime']
    numeric_cols = [col for col in df.columns if col not in exclude_cols and pd.api.types.is_numeric_dtype(df[col])]
    
    # Aggregate statistics: mean, max, min for numeric columns
    agg_mean = df[numeric_cols].mean().rename(lambda x: x + '_mean')
    agg_max = df[numeric_cols].max().rename(lambda x: x + '_max')
    agg_min = df[numeric_cols].min().rename(lambda x: x + '_min')
    
    summary = pd.concat([agg_mean, agg_max, agg_min])
    
    # Convert summary DataFrame to dict (key: metric_column, value: metric_value)
    report_dict = summary.to_dict()
    
    # Push to XCom
    kwargs['ti'].xcom_push(key='daily_aggregation_report', value=report_dict)
    print(f"Aggregated report is generated: {report_dict}")
    return report_dict


with DAG(
    'daily_data_aggregation_dag',
    default_args=default_args,
    description='Aggregate daily sensor data and generate report',
    schedule_interval="0 6 * * *",  # Daily at 6 AM
    start_date=datetime(2025, 6, 12),
    catchup=False,
    tags=['aggregation', 'daily'],
) as dag:

    aggregate_task = PythonOperator(
        task_id='aggregate_daily_data',
        python_callable=aggregate_daily_data,
        provide_context=True,
    )
