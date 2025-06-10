# Base image with Python 3.10
FROM python:3.10

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages for stream processing
RUN pip install --no-cache-dir \
    kafka-python==2.0.2 \
    numpy==1.24.3 \
    pyspark==3.4.1

# Create necessary directories
RUN mkdir -p ./data_processing/stream_processing \
    ./config \
    ./app/utils \
    ./data/checkpoints \
    ./data/processed_stream

# Copy application code
COPY data_processing/stream_processing/ ./data_processing/stream_processing/
COPY config/ ./config/
COPY app/utils/ ./app/utils/
COPY .env ./

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
CMD ["python", "data_processing/stream_processing/transform_and_save_stream.py"]
