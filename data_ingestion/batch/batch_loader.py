import pandas as pd
from data_ingestion import utils

csv_file_path = utils.kaggle_data_file_path

def load_batch_data(csv_file_path: str):
    return pd.read_csv(csv_file_path, header=True)

