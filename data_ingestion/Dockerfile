# Base image with Python 3.10
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p ./app/utils ./data_ingestion ./config

# Copy data_ingestion folder into container
COPY data_ingestion/ ./data_ingestion/
COPY ../config/ ./config/
COPY ../app/utils/ ./app/utils/
COPY ../.env ./

