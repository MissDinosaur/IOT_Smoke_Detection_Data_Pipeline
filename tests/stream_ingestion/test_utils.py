import pytest
from data_ingestion import utils
from app.utils.path_utils import ROOT_DIR
from config.constants import TARGET_COLUMN


def test_constant_varaible():
    expected_kaggle_file_path = ROOT_DIR / "data/smoke_detection_iot.csv"
    assert utils.KAGGLE_DATA_FILE_PATH == expected_kaggle_file_path
    # assert utils.KAGGLE_DATA_FILE_PATH.resolve(strict=False) == expected_kaggle_file_path.resolve(strict=False)

def test_load_schema():
    schema = utils.load_kaggle_data_schema(utils.KAGGLE_DATA_FILE_PATH)
    target_col_schema_value = {
                'type': 'categorical',
                'values': ["0", "1"]
            }
    assert schema[TARGET_COLUMN] == target_col_schema_value