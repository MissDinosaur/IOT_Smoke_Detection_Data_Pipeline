import os
import pandas as pd

TMP_DIR = '/tmp/airflow_smoke_pipeline'

def clean_data(**kwargs):
    raw_path = kwargs['ti'].xcom_pull(key='data_path')
    df = pd.read_csv(raw_path)

    # Fill missing values in numeric columns only, with median
    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())


    # Drop duplicates
    df.drop_duplicates(inplace=True)

    # Filter invalid temperature and humidity ranges
    df['Temperature[C]'] = pd.to_numeric(df['Temperature[C]'], errors='coerce')
    df = df[(df['Temperature[C]'] > -50) & (df['Temperature[C]'] < 100)]
    df['Humidity[%]'] = pd.to_numeric(df['Humidity[%]'], errors='coerce')
    df = df[(df['Humidity[%]'] >= 0) & (df['Humidity[%]'] <= 100)]

    # Convert UTC to datetime and add features
    df['datetime'] = pd.to_datetime(df['UTC'], unit='s')
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek

    cleaned_path = os.path.join(TMP_DIR, 'cleaned_data.csv')
    df.to_csv(cleaned_path, index=False)
    kwargs['ti'].xcom_push(key='cleaned_path', value=cleaned_path)
