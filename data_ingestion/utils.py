import csv
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np


load_dotenv() # Load variables from .env
kaggle_data_file = os.getenv("DATA_FILE_NAME")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
kaggle_data_file_path = os.path.join(ROOT_DIR, "data", kaggle_data_file)

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"

def get_csv_headers(filepath: str =kaggle_data_file_path) -> list[str]: 
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Read the first line
    return headers

def load_schema(referred_csv_path: str =kaggle_data_file_path) -> dict:
    """Derive the data description of the csv data file"""
    df = pd.read_csv(referred_csv_path)
    schema = {}
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64]:
            schema[col] = {
                'type': 'numeric',
                'min': df[col].min(),
                'max': df[col].max(),
                'mean': df[col].mean(),
                'std': df[col].std()
            }
        else:
            schema[col] = {
                'type': 'categorical',
                'values': df[col].dropna().unique().tolist()
            }
    return schema
