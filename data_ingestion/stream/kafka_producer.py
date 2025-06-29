import sys
from pathlib import Path

# Get the current absolute path：/app/data_ingestion/stream/kafka_producer.py
current_file = Path(__file__).resolve()

# get the root
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import json
import config.env_config as cfg
from data_ingestion import utils
import simulate_stream_data as sim


def kafka_produce_and_send_data(missing_rate, interval=2.0, topic=cfg.KAFKA_TOPIC_SMOKE):
    """
    Generate and sent synthetic data by Kafka every 2 senconds
    missing_rate: The rate of exisiting NULL values
    interval: The interval of generating data
    topic: Kafka topic
    """
    try:
        while True:
            try:
                producer = KafkaProducer(
                    bootstrap_servers=[cfg.KAFKA_BOOTSTRAP_SERVERS],
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                )
                print("Producer is created.")
                break
            except NoBrokersAvailable:
                print("Kafka broker not available, retrying...")
                time.sleep(10)
        print(f"Kafka producer initialized. Topic: {topic}")

        print("Start generating synthetic data...")
        schema = utils.load_kaggle_data_schema()
        count = 0
        current_timestamp = int(time.time())
        while True:
            row: dict = sim.generate_random_row(
                schema, current_timestamp, missing_rate
            )  # existing 5% missing by default
            count += 1
            current_timestamp += int(interval)
            print(f"Generated {count}th row data: {row}")

            # Send the dictionary directly - the serializer will handle JSON encoding
            producer.send(topic=topic, value=row)
            producer.flush()  # make sure message has been sent
            print(f"{count}th Row data sent")

            time.sleep(interval) # produce a new data every specific seconds

    except Exception as e:
        print(e)


if __name__ == "__main__":
    kafka_topic = cfg.KAFKA_TOPIC_SMOKE
    print(f"kafka_topic: {kafka_topic}")
    print(f"cfg.KAFKA_BOOTSTRAP_SERVERS: {cfg.KAFKA_BOOTSTRAP_SERVERS}")
    kafka_produce_and_send_data(missing_rate=0.05, interval=2.0, topic=kafka_topic)
