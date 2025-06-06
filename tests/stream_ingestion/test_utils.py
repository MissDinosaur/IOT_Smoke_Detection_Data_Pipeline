import pytest
from data_ingestion import utils
from app.utils.path_utils import ROOT_DIR
from config.constants import TARGET_COLUMN


def test_constant_varaible():
    expected_kaggle_file_path = ROOT_DIR / "data/smoke_detection_iot.csv"
    assert utils.KAGGLE_DATA_FILE_PATH == expected_kaggle_file_path
    # assert utils.KAGGLE_DATA_FILE_PATH.resolve(strict=False) == expected_kaggle_file_path.resolve(strict=False)

def test_get_csv_headers():
    expected_data = ["UTC", "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]", "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5", "NC0.5", "NC1.0", "NC2.5", "CNT", "Fire Alarm"]
    assert utils.get_kaggle_data_headers(utils.KAGGLE_DATA_FILE_PATH) == expected_data


def test_load_schema():
    schema = utils.load_kaggle_data_schema(utils.KAGGLE_DATA_FILE_PATH)
    target_col_schema_value = {
                'type': 'categorical',
                'values': ["0", "1"]
            }
    assert schema[TARGET_COLUMN] == target_col_schema_value