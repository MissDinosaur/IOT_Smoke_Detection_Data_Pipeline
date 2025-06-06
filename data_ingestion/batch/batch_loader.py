import pandas as pd
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import KAGGLE_DATA_FILE, TARGET_COLUMN


kaggle_file_path = build_relative_path(DATA_DIR, KAGGLE_DATA_FILE)

def load_csv_data(file_path: str =kaggle_file_path):
    df = pd.read_csv(file_path, index_col=0)
    df[TARGET_COLUMN] = pd.Categorical(df[TARGET_COLUMN].astype(str))  # convert TARGET_COLUMN to categorical column
    return df

