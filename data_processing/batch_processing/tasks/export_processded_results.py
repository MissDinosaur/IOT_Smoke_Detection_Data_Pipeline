import os
import pandas as pd
from google.cloud import bigquery
from config.constants import PROCESSED_HISTORICAL_FILE_PREFIX
from datetime import datetime, timedelta
from config.constants import PROCESSED_HISTORICAL_FILE_PREFIX

today = datetime.now()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.date().strftime("%Y-%m-%d")

PROCESSED_HISTORICAL_DATA_FILE_NAME = PROCESSED_HISTORICAL_FILE_PREFIX + "_" + yesterday_str + ".csv"
LOCAL_OUTPUT_DIR = '/opt/airflow/output/'
LOCAL_OUTPUT_PATH = os.path.join(LOCAL_OUTPUT_DIR, PROCESSED_HISTORICAL_DATA_FILE_NAME)

def export_results(**kwargs):
    features_path = kwargs['ti'].xcom_pull(key='features_path')
    df = pd.read_csv(features_path)

    # Save locally
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    df.to_csv(LOCAL_OUTPUT_PATH, index=False)
    print("dataframe is saved in .csv")

    # Export to BigQuery
    #client = bigquery.Client()
    #table_id = 'your-project.your_dataset.smoke_features'  # Replace with your table ID

    #job_config = bigquery.LoadJobConfig(
    #    autodetect=True,
    #    write_disposition="WRITE_TRUNCATE"
    #)
#
    #job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    #job.result()
