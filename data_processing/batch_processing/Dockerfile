# Use official Apache Airflow image based on Python 3.10
FROM apache/airflow:2.7.1-python3.10

# Switch to root to install additional dependencies if needed
USER root

# Install additional packages if you need (example: pandas, google-cloud-bigquery etc.)
RUN pip install --no-cache-dir pandas google-cloud-bigquery

# Switch back to airflow user
USER airflow

# Copy dags and tasks are mounted via volumes in docker-compose, no need to copy here

# Entrypoint and cmd are handled by docker-compose command
