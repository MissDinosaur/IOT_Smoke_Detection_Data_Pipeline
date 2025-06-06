import os
import json
from kafka import KafkaConsumer
from app.utils.path_utils import DATA_DIR, build_relative_path
from config.constants import NULL_MARKER, GROUP_ID, HISTORICAL_DATA_FILE  
from config.env_config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_SMOKE
from data_ingestion import utils


columns = utils.get_kaggle_data_headers()

def save_historical_data(row, output_csv_file:str):
    """Save data into csv file row by row"""
    # If output_csv file doesn't exist or it's empty then it is the first time to write sth into this file
    first_time_flg = not os.path.exists(output_csv_file) or os.path.getsize(output_csv_file) == 0
    with open(output_csv_file, 'a', encoding='utf-8') as f:
        # If it is the first time to write sth into this file, then write the header first
        if first_time_flg:
            f.write(','.join(columns) + '\n')  # Write header
        f.write(','.join(row) + '\n')
        f.flush()  # flush to disk immediately

def consume_streaming_data(topic, output_csv, group_id):
    """
    Only Consume messages from Kafka topic and append to CSV file.
    You can add more data processing operations here.
    """

    # Initialize Kafka consumer
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',  # start from beginning if no offset
        enable_auto_commit=True,
        group_id=group_id,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    print(f"Consuming from Kafka topic '{topic}' and writing to '{output_csv}'...")
    # Consume messages continuously
    for message in consumer:
        data = message.value  # a dict decoded from JSON

        # Prepare row values in correct column order
        row = []
        for col in columns:
            val = data.get(col)
            val = NULL_MARKER if val is None else val
            row.append(str(val))

        save_historical_data(row, output_csv)
        #print(f"Appended row: {row}")
        # You can add more data processing operations here 

if __name__ == '__main__':
    historical_data_file_path = build_relative_path(DATA_DIR, HISTORICAL_DATA_FILE)
    print(f"historical_data_file_path: {historical_data_file_path}")
    consume_streaming_data(KAFKA_TOPIC_SMOKE, historical_data_file_path, group_id=GROUP_ID)
