from config.constants import CLEANED_DATA_FILE
from app.utils.path_utils import DATA_DIR, build_relative_path
from data_ingestion.batch import batch_loader as bl

cleaned_data_file_path = build_relative_path(DATA_DIR, CLEANED_DATA_FILE)

def compute_metrics():
    df = bl.load_csv_data(cleaned_data_file_path)
    report = {}
    report["shape"] = df.shape
    print(f"[INFO] Dataset shape: {df.shape}")
    print("[INFO] Fire Alarm distribution:")
    report["Fire_Alarm_distribution"] = df["Fire Alarm"].value_counts()
    print(df["Fire Alarm"].value_counts())

    print("[INFO] Basic stats:")
    report["table_description"] = df.describe()
    print(df.describe())

    return report
