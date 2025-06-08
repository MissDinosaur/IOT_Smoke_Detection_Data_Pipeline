import os


# ---------------- zookeeper Config ----------------
ZOOKEEPER_CLIENT_PORT = os.getenv("ZOOKEEPER_CLIENT_PORT", "2181")

# --------------- Kafka Config ---------------
KAFKA_PORT = os.getenv("KAFKA_PORT", "9092")
KAFKA_BROKER_ID = int(os.getenv("KAFKA_BROKER_ID", 1))
KAFKA_ZOOKEEPER_CONNECT = "zookeeper:" + ZOOKEEPER_CLIENT_PORT
KAFKA_TOPIC_SMOKE = os.getenv("KAFKA_TOPIC_SMOKE", "smoke_sensor_data")
KAFKA_BOOTSTRAP_SERVERS = "kafka:" + KAFKA_PORT

# --------------- Flask API ---------------
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = os.getenv("FLASK_PORT", "5000")

# --------------- Airflow ---------------
AIRFLOW_UID = os.getenv("AIRFLOW_UID", "50000")
AIRFLOW_GID = os.getenv("AIRFLOW_GID", "0")
AIRFLOW_EXECUTOR = os.getenv("AIRFLOW__CORE__EXECUTOR", "LocalExecutor")
AIRFLOW_FERNET_KEY = os.getenv("AIRFLOW__CORE__FERNET_KEY", "your_fernet_key_here")
AIRFLOW_USER = os.getenv("AIRFLOW__WEBSERVER__DEFAULT_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW__WEBSERVER__DEFAULT_PASSWORD", "admin")

# --------------- ML Model ---------------
MODEL_PATH = os.getenv("MODEL_PATH", "models/smoke_detection_model.pkl")

# --------------- Monitoring ---------------
PROMETHEUS_PORT = os.getenv("PROMETHEUS_PORT","9090")
GRAFANA_PORT = os.getenv("GRAFANA_PORT", "3000")
