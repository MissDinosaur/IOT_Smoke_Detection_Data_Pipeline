import pytest
from data_processing import utils

def test_get_csv_headers():
    expected_data = ["UTC", "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]", "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5", "NC0.5", "NC1.0", "NC2.5", "CNT", "Fire Alarm"]
    assert utils.get_kaggle_data_headers(utils.KAGGLE_DATA_FILE_PATH) == expected_data
