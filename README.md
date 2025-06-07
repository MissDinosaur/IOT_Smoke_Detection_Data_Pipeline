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
├── app/                                    # Web Application logic
│   ├── api                                     # Flask backend 
│   │   ├── metrics_api.py                        # API to serve monitoring metrics
│   │   └── prediction_api.py                     # API to handle user input and return prediction  
│   ├── ui                                      # Flask frontend 
│   │    ├── templates/                           # HTML upload page or try-on viewer
│   │    └── static/                              # CSS, JS, webcam script, glasses
│   ├── utils/                                  # Include path control tool
│   └── __init__.py                             # Flask initialization 
│   
├── config/                                 # Configuration folder
│   ├── constants.py                            # Contains global constant variables
│   └── env_config.py                           # Fetch the environment variables
|   
├── data    
│   ├── smoke_detection_iot.csv 
│   └── historical_smoke_data.csv   
|   
├── data_ingestion/                         # Ingest data from stream and batch sources
│   ├── stream/ 
│   │   ├── kafka_producer.py                   # Send streaming data to Kafka
│   │   └── simulate_stream_data.py             # Continuously generate mock sensor data
│   └── batch/  
│   │   └── batch_loader.py                     # Load historical sensor data from file
│   └── utils.py
│
├── data_processing/
│   ├── stream_processing/
│   │   ├── transform_and_save_stream.py.py     # Real-time transformation and feature extraction and saving
│   │   ├── detect_anomalies.py                 # Smoke anomaly detection logic
│   │   └── metrics_streaming.py                # Compute live stream analytics
│   ├── batch_processing/   
│   │   ├── dags/   
│   │   │   └── smoke_detection_dag.py          # Airflow DAG for batch pipeline
│   │   ├── tasks/  
│   │   │   ├── compute_batch_metrics.py        # Batch-level data quality and KPI metrics
│   │   │   └── feature_engineering.py          # Feature processing for ML
│   └── utils.py                            # Shared data processing helper functions
│
├── ml_model/
│   ├── training/
│   │   ├── train_model.py                  # Train ML model for smoke detection
│   │   └── evaluate_model.py               # Model evaluation logic
│   ├── inference/
│   │   ├── model_loader.py                 # Load trained model
│   │   ├── predict.py                      # Run prediction from script
│   │   └── predict_wrapper.py              # Prediction module used by API
│   └── models/
│       └── smoke_model.pkl                 # Trained model file
│
├── monitoring/                             # Monitor data & processing metrics
│   ├── prometheus_exporter.py                  # Expose metrics to Prometheus
│   ├── log_metrics.py                          # Log data volume, latency, error rate, etc.
│   └── dashboards/ 
│       └── grafana_dashboard.json              # Grafana dashboard configuration
│
├── tests/                                  # Unit and integration tests
│   
├── docker-compose.yml                      # Includes Kafka, Airflow, Prometheus, Flask
├── main.py                                 # Script to start application
├── README.md                               # Project documentation and instructions
├── .env.example                            # Global/shared environment config
└──requirements.txt

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
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <project-folder-name>
   ```

2. **Generate and edit .env file**

    Rename .env.example as .env in the root directory and edit it according to your actual case.
    ```bash
    cp .env.example .env
    ```
3. **Set up the dataset**
    
    This project uses the [Smoke Detection Dataset](https://www.kaggle.com/datasets/deepcontractor/smoke-detection-dataset) from Kaggle.

    How to set up the dataset
    1. Visit the [Kaggle dataset page](https://www.kaggle.com/datasets/deepcontractor/smoke-detection-dataset)
    2. Download the CSV file (e.g., `smoke_detection_iot.csv`)
    3. Place it inside the `data/` directory in the project root.

    For more detailed instructions, see [`data/README.md`](data/README.md).

4. **Build and start all services using Docker Compose**
    ```bash
   docker-compose up --build
   ```
    This command will:

    Build the Flask app image, 

    And start:

    - Flask API server
    - Apache Kafka and Zookeeper
    - Airflow scheduler and web UI
    - Prometheus 
    - Grafana 

5. (Optional) **Run CLI commands inside containers**
    ```bash
    # You can run Kafka producer/consumer, Airflow CLI, or training scripts inside containers:
    # Replace smoke_flask_app with relevant container name or container id
    docker exec -it smoke_flask_app bash


    ```
5. (Optional) **Stop and remove containers**
    ```bash
    docker-compose down

    # Use --volumes if you want to delete persistent data (Grafana dashboards, etc.):
    docker-compose down --volumes
    ```