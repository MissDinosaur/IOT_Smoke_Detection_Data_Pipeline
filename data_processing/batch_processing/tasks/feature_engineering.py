# batch_processing/tasks/feature_engineering.py
from config.constants import CLEANED_DATA_FILE
from app.utils.path_utils import DATA_DIR, build_relative_path
from data_ingestion.batch import batch_loader as bl

cleaned_data_file_path = build_relative_path(DATA_DIR, CLEANED_DATA_FILE)

def run_feature_engineering():
    df = bl.load_csv_data()

    # Clean：remove missing value or anomoly
    df.dropna(inplace=True)
    df = df[df["Temperature[C]"] > -40]

    # Create a new feature
    df["Temp_Humidity_Ratio"] = df["Temperature[C]"] / (df["Humidity[%]"] + 1e-5)

    # Save data after data featuring 
    df.to_csv(cleaned_data_file_path, index=False)
    print(f"[INFO] Feature-engineered data saved to {cleaned_data_file_path}")
