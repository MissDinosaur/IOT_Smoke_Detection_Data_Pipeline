import time
import os
from kafka import KafkaProducer
import json
import simulate_stream_data as sim
from data_ingestion import utils


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def produce_and_send_data(missing_rate, interval=2.0, kafka_topic=None):
    producer = None
    if kafka_topic:
        producer = KafkaProducer(
            bootstrap_servers=[utils.KAFKA_BOOTSTRAP_SERVERS],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Kafka producer initialized. Topic: {kafka_topic}")
    
    print("Start generating synthetic data...")
    while True:
        row: dict = sim.generate_random_row(missing_rate=missing_rate)  # existing 5% missing by default
        # print(row)

        message = json.dumps(row).encode('utf-8')
        producer.send(topic=kafka_topic, value=message)

        time.sleep(interval) # produce a new data every specific seconds

if __name__ == "__main__":
    historical_data_file = os.path.join(ROOT_DIR, "data", "historical_smoke_data.csv")
    kafka_topic = "smoke_sensor_data"
    produce_and_send_data(missing_rate=0.05, kafka_topic=kafka_topic)
