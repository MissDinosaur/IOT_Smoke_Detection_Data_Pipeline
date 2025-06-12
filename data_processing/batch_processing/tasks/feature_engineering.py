import os
import pandas as pd
from sklearn.preprocessing import Normalizer

TMP_DIR = '/tmp/airflow_smoke_pipeline'

def feature_engineering(**kwargs):
    cleaned_path = kwargs['ti'].xcom_pull(key='cleaned_path')
    df = pd.read_csv(cleaned_path)

    # Create rwo new features
    df['Temp_Humidity_Product'] = df['Temperature[C]'] * df['Humidity[%]']
    df['PM_sum'] = df['PM1.0'] + df['PM2.5']

    # Normalize columns except UTC and target 'Fire Alarm'
    cols_to_normalize = df.columns.drop(['UTC', 'Fire Alarm', 'datetime', 'hour', 'day_of_week'])
    scaler = Normalizer()
    df[cols_to_normalize] = scaler.fit_transform(df[cols_to_normalize])

    features_path = os.path.join(TMP_DIR, 'features.csv')
    df.to_csv(features_path, index=False)
    kwargs['ti'].xcom_push(key='features_path', value=features_path)
