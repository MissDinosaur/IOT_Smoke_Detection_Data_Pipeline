import csv
import pandas as pd
import numpy as np
from batch.batch_loader import load_csv_data
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import KAGGLE_DATA_FILE


KAGGLE_DATA_FILE_PATH = build_relative_path(DATA_DIR, KAGGLE_DATA_FILE)
print(f"KAGGLE_DATA_FILE_PATH: {KAGGLE_DATA_FILE_PATH}")

def get_kaggle_data_headers(file_path: str =KAGGLE_DATA_FILE_PATH) -> list[str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)[1:]  # Read the first line, excluding the first element
    return headers

def load_kaggle_data_schema(referred_csv_path: str =KAGGLE_DATA_FILE_PATH) -> dict:
    """
    Load schema based on Kaggle batch data.
    Depends on batch_loader, which is a low-level CSV loading module.
    """
    df = load_csv_data(referred_csv_path)
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
