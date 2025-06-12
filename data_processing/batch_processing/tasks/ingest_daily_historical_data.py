import os
import pandas as pd
from datetime import datetime, timedelta
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import HISTORICAL_DATA_FILE_PREFIX

TMP_DIR = '/tmp/airflow_smoke_pipeline'
os.makedirs(TMP_DIR, exist_ok=True)

today = datetime.now()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.date().strftime("%Y-%m-%d")

HISTORICAL_DATA_FILE_NAME = HISTORICAL_DATA_FILE_PREFIX + "_" + yesterday_str + ".csv"
DATA_FILE_FROM_PREVIOUS_DAY = build_relative_path(DATA_DIR, HISTORICAL_DATA_FILE_NAME)

def ingest_data(**kwargs):
    if not os.path.exists(DATA_FILE_FROM_PREVIOUS_DAY):
        raise FileNotFoundError(f"File {DATA_FILE_FROM_PREVIOUS_DAY} does not exist.")    
    df = pd.read_csv(DATA_FILE_FROM_PREVIOUS_DAY)
    tmp_path = os.path.join(TMP_DIR, HISTORICAL_DATA_FILE_NAME)
    df.to_csv(tmp_path, index=False)
    kwargs['ti'].xcom_push(key='data_path', value=tmp_path)
