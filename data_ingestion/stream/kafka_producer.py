import time
from kafka import KafkaProducer
import json
import config.env_config as cfg
from data_ingestion import utils
import simulate_stream_data as sim


def kafka_produce_and_send_data(missing_rate, interval=2.0, topic=cfg.KAFKA_TOPIC_SMOKE):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[cfg.KAFKA_BOOTSTRAP_SERVERS],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Kafka producer initialized. Topic: {topic}")
    
        print("Start generating synthetic data...")
        schema = utils.load_schema()
        while True:
            row: dict = sim.generate_random_row(schema, missing_rate)  # existing 5% missing by default
            # print(row)

            message = json.dumps(row).encode('utf-8')
            producer.send(topic=topic, value=message)
            producer.flush()  # make sure message has been sent
            
            time.sleep(interval) # produce a new data every specific seconds
    except Exception as e:
        print(e)

if __name__ == "__main__":
    kafka_topic = cfg.KAFKA_TOPIC_SMOKE
    kafka_produce_and_send_data(missing_rate=0.05, interval=2.0, topic=kafka_topic)
