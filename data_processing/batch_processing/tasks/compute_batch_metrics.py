from config.constants import CLEANED_DATA_FILE
from app.utils.path_utils import DATA_DIR, build_relative_path
from data_ingestion.batch import batch_loader as bl

cleaned_data_file_path = build_relative_path(DATA_DIR, CLEANED_DATA_FILE)

def compute_metrics(file_path: str =cleaned_data_file_path):
    df = bl.load_csv_data(file_path)
    report = {}
    report["shape"] = df.shape
    print(f"[INFO] Dataset shape: {df.shape}")
    
    fire_alarm_dist = df["Fire Alarm"].value_counts()
    # Airflow's XCom (used for communication between tasks) uses JSON serialization by default,
    # and Series/DataFrame can't be serialized to JSON directly.
    # So, need to convert non-serializable objects to JSON-serializable ones
    report["Fire_Alarm_distribution"] = fire_alarm_dist.to_dict()
    print("[INFO] Fire Alarm distribution:")
    print(fire_alarm_dist)

    description = df.describe()
    # convert non-serializable objects to JSON-serializable ones
    report["table_description"] = description.to_dict()
    print("[INFO] Basic stats:")
    print(description)

    return report
