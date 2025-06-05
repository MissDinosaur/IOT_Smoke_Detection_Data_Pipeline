import os
import json
from kafka import KafkaConsumer
from data_ingestion import utils


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
GROUP_ID='consumer_1'
NULL_MARKER = "<NULL>"

columns = utils.get_csv_headers()

def save_historical_data(row, output_csv_file:str):
    # If output_csv file doesn't exist or it's empty then it is the first time to write sth into this file
    first_time_flg = not os.path.exists(output_csv_file) or os.path.getsize(output_csv_file) == 0
    with open(output_csv_file, 'a', encoding='utf-8') as f:
        # If it is the first time to write sth into this file, then write the header first
        if first_time_flg:
            f.write(','.join(columns) + '\n')  # Write header
        f.write(','.join(row) + '\n')
        f.flush()  # flush to disk immediately

def consume_to_csv(topic, output_csv, group_id):
    """
    Consume messages from Kafka topic and append to CSV file.
    Args:
        topic (str): Kafka topic to consume from
        output_csv (str): Path to output CSV file
        group_id (str): Kafka consumer group ID
    """

    # Initialize Kafka consumer
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=utils.KAFKA_BOOTSTRAP_SERVERS,
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

if __name__ == '__main__':
    kafka_topic = "smoke_sensor_data"
    csv_file = os.path.join(ROOT_DIR, "data", "historical_smoke_data.csv")

    consume_to_csv(kafka_topic, csv_file, group_id=GROUP_ID)
