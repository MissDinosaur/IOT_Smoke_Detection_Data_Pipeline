# Base image with Python 3.10
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy data_ingestion folder into container
COPY data_ingestion/ .

# Default command: can be overridden by docker-compose
CMD ["python", "stream/kafka_producer.py"]
