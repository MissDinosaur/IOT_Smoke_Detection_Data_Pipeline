import pytest
import data_ingestion.stream.simulate_stream_data as sim
from data_ingestion.utils import load_kaggle_data_schema
import time

current_timestamp = int(time.time())

def test_generate_random_row():
    schema = load_kaggle_data_schema()
    row = sim.generate_random_row(schema=schema, current_timestamp=current_timestamp)

    assert isinstance(row, dict)
    assert row   # not empty

    keys = list(row.keys())
    expected_keys = ["UTC", "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]", "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5", "NC0.5", "NC1.0", "NC2.5", "CNT", "Fire Alarm"]

    assert keys==expected_keys

