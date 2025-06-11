# Use official Apache Airflow image based on Python 3.10
FROM apache/airflow:2.7.1-python3.10


USER airflow

# Install additional packages if you need (example: pandas, google-cloud-bigquery etc.)
RUN pip install pandas numpy

# Copy dags and tasks are mounted via volumes in docker-compose, no need to copy here

# Entrypoint and cmd are handled by docker-compose command
