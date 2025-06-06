import csv
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import KAGGLE_DATA_FILE


KAGGLE_DATA_FILE_PATH = build_relative_path(DATA_DIR, KAGGLE_DATA_FILE)
print(f"KAGGLE_DATA_FILE_PATH: {KAGGLE_DATA_FILE_PATH}")

def get_kaggle_data_headers(file_path: str =KAGGLE_DATA_FILE_PATH) -> list[str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)[1:]  # Read the first line, excluding the first element
    return headers