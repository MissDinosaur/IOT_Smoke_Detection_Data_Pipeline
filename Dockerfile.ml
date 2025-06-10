# Dockerfile for ML Service
# Dedicated container for ML model serving and predictions

FROM python:3.10-slim

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional ML-specific dependencies
RUN pip install --no-cache-dir \
    flask-cors \
    gunicorn \
    prometheus-client

# Copy application code
COPY ml/ /app/ml/
COPY config/ /app/config/
COPY data_processing/business_logic/ /app/data_processing/business_logic/

# Create necessary directories
RUN mkdir -p /app/ml/models \
    && mkdir -p /app/logs \
    && mkdir -p /app/data

# Create non-root user
RUN groupadd -r mluser && useradd -r -g mluser mluser
RUN chown -R mluser:mluser /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to non-root user
USER mluser

# Expose ML API port
EXPOSE 5000

# Default command - start ML API server
CMD ["python", "-m", "ml.inference.predict_wrapper"]
