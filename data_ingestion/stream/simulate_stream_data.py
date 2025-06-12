import numpy as np
from datetime import datetime
import random


def generate_random_row(schema: dict, current_timestamp: int, missing_rate: float =0.05) -> dict:
    """Generate synthetic data according to the schema of the original Kaggle smoke data. 
        And there exist missing values in the data with the specific rate.
    """
    row = {}
    for col, info in schema.items():
        if random.random() < missing_rate:
            row[col] = None
            continue
        if col.lower() == 'timestamp':
            row[col] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif col.lower() == 'utc':
            row[col] = current_timestamp
        elif info['type'] == 'numeric':
            value = np.random.normal(loc=info['mean'], scale=info['std'])
            value = np.clip(value, info['min'], info['max'])
            row[col] = round(value, 2)
        elif info['type'] == 'categorical':
            row[col] = random.choice(info['values'])
        else:
            row[col] = None
    return row
