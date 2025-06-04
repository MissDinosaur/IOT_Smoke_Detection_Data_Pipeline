# IoT Smoke Detection Data Pipeline
##  Project Overview
This project implements a full-stack data pipeline for real-time and batch processing of IoT-based smoke detection data. It simulates sensor data from smoke detectors, processes both streaming and historical data, performs anomaly detection and machine learning-based prediction, and exposes insights through a monitoring dashboard and interactive UI.

The system integrates key components of a modern data pipeline:
- **Data Generation**: Simulates live smoke sensor data streams and generates historical datasets.
- **Data Ingestion**: Ingests both streaming data (via Kafka) and batch data (via Airflow-managed pipelines).
- **Stream Processing**: Cleans and transforms incoming real-time data, detecting anomalies such as sudden smoke level spikes.
- **Batch Processing**: Uses Apache Airflow to schedule and manage historical data analysis and metric computation.
- **Machine Learning**: Trains a classification model to predict smoke-related events or alarms using engineered features.
- **Monitoring**: Logs and exports key performance metrics (data volume, latency, errors) via Prometheus and displays them in - **Grafana.
- **Frontend Dashboard**: A Flask-based web interface shows live metrics, allows interactive prediction, and visualizes system health.

## Project Structure
```text
iot_smoke_detection_data_pipeline/
│
├── app/                                 # Frontend Dashboard logic
│   ├── api                                # Flask backend 
│   │   ├── metrics_api.py                   # API to serve monitoring metrics
│   │   └── prediction_api.py                # API to handle user input and return prediction  
│   ├── ui                                 # Flask frontend 
│   │    ├── templates/                      # HTML upload page or try-on viewer
│   │    └── static/                         # CSS, JS, webcam script, glasses
│   ├── utils/
│   └── __init__.py                          # Flask initialization 
|
├── data_generation/                     # Simulate IoT smoke sensor data
│   ├── simulate_stream_data.py              # Continuously push mock data to Kafka
│   ├── generate_historical_data.py          # Generate historical CSV/Parquet data
│   └── config/
│       └── sensor_schema.yaml               # Schema definition for sensor data
│
├── data_ingestion/                      # Ingest data from stream and batch sources
│   ├── stream_ingestion/
│   │   ├── kafka_producer.py                # Send streaming data to Kafka
│   │   ├── kafka_consumer.py                # Consume real-time sensor data
│   └── batch_ingestion/
│       ├── batch_loader.py                  # Load historical sensor data from file
│       └── file_monitor.py                  # Monitor folder for new batch files
│
├── processing/
│   ├── stream_processing/
│   │   ├── transform_stream.py              # Real-time transformation and feature extraction
│   │   ├── detect_anomalies.py              # Smoke anomaly detection logic
│   │   └── metrics_streaming.py             # Compute live stream analytics
│   ├── batch_processing/
│   │   ├── dags/
│   │   │   ├── smoke_detection_dag.py       # Airflow DAG for batch pipeline
│   │   │   └── sensors.py                   # Custom sensors for Airflow DAG
│   │   ├── tasks/
│   │   │   ├── feature_engineering.py       # Feature processing for ML
│   │   │   ├── train_trigger.py             # Optionally trigger training
│   │   │   └── compute_batch_metrics.py     # Batch-level data quality and KPI metrics
│   │   └── airflow.cfg                      # Local Airflow configuration (optional)
│   └── utils/
│       └── cleaning_utils.py                # Shared data cleaning helper functions
│
├── ml_model/
│   ├── training/
│   │   ├── train_model.py                   # Train ML model for smoke detection
│   │   └── evaluate_model.py                # Model evaluation logic
│   ├── inference/
│   │   ├── model_loader.py                  # Load trained model
│   │   ├── predict.py                       # Run prediction from script
│   │   └── predict_wrapper.py               # Prediction module used by API
│   └── models/
│       └── smoke_model.pkl                  # Trained model file
│
├── monitoring/                          # Monitor data & processing metrics
│   ├── prometheus_exporter.py               # Expose metrics to Prometheus
│   ├── log_metrics.py                       # Log data volume, latency, error rate, etc.
│   └── dashboards/
│       └── grafana_dashboard.json           # Grafana dashboard configuration
│
├── docker/                             # Docker + Docker Compose setup
│   ├── docker-compose.yml                   # Includes Kafka, Airflow, Prometheus, Flask
│   ├── Dockerfile.pipeline                  # For data pipeline services
│   └── Dockerfile.frontend                  # For Flask dashboard service
│
├── tests/                                   # Unit and integration tests
│   ├── test_kafka_ingestion.py
│   ├── test_model_prediction.py
│   └── test_flask_api.py
│
├── main.py                             # Script to start app
├── README.md                           # Project documentation and instructions
├── project_config.yaml                 # Global/shared config
└── requirements.txt                    # Python dependency list

```


## Tech Stack

#### Languages & Libraries
- **Python** – Core language for pipeline, ML, and APIs (recommand version 3.10.xx) 
- **Pandas / NumPy** – Data manipulation and preprocessing  
- **Scikit-learn** – Model training and evaluation  
- **Flask** – API and dashboard server  

#### Data Streaming & Messaging
- **Apache Kafka** – Real-time data pipeline and transport

#### Batch Processing & Workflow
- **Apache Airflow** – Batch data processing orchestration and scheduling

#### Machine Learning
- **Scikit-learn** – Smoke event prediction with classification models  

#### Monitoring & Observability
- **Prometheus** – Collect system/data pipeline metrics  
- **Grafana** – Real-time visualization dashboard

#### Web & Frontend
- **Flask** – Web API + simple dashboard  
- **HTML/CSS** – UI layout and styling 

#### Containerization & DevOps
- **Docker** – Isolated service containers  
- **Docker Compose** – Service orchestration (Kafka, Airflow, Prometheus, etc.)

##  Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <project-folder-name>
   ```

2. Rename .env.example as .env and edit according to your actual case
    ```bash
    cp .env.example .env
    ```

3. Build and start all services using Docker Compose
    ```bash
   docker-compose -f docker/docker-compose.yml up --build
   ```
    This command will:

    Build the Flask app image

    Start:

    - Flask API server
    - Apache Kafka and Zookeeper
    - Airflow scheduler and web UI
    - Prometheus 
    - Grafana 

4. (Optional) Run CLI commands inside containers
    ```bash
    # You can run Kafka producer/consumer, Airflow CLI, or training scripts inside containers:
    # Replace smoke_flask_app with relevant container name or container id
    docker exec -it smoke_flask_app bash


    ```
5. (Optional) Stop and remove containers
    ```bash
    docker-compose down

    # Use --volumes if you want to delete persistent data (Grafana dashboards, etc.):
    docker-compose down --volumes
    ```