import pandas as pd
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import KAGGLE_DATA_FILE


csv_file_path = build_relative_path(DATA_DIR, KAGGLE_DATA_FILE)

def load_batch_data(csv_file_path: str):
    return pd.read_csv(csv_file_path, index_col=0)

