# Dockerfile for ML Service
# Dedicated container for ML model serving and predictions

FROM python:3.10

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV FONTCONFIG_PATH=/tmp/fontconfig

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching (use ultra-minimal)
COPY requirements_ultra_minimal.txt /app/requirements_ultra_minimal.txt

# Install ultra-minimal requirements first
RUN pip install --no-cache-dir -r requirements_ultra_minimal.txt

# Install additional packages needed for ML (one by one)
RUN pip install --no-cache-dir scipy==1.10.1
RUN pip install --no-cache-dir joblib==1.3.2
RUN pip install --no-cache-dir matplotlib==3.7.2
RUN pip install --no-cache-dir seaborn==0.12.2
RUN pip install --no-cache-dir schedule

# Install additional ML-specific dependencies
RUN pip install --no-cache-dir flask-cors gunicorn prometheus-client

# Copy application code
COPY ml/ /app/ml/
COPY config/ /app/config/
COPY data_ingestion/ /app/data_ingestion/
COPY app/ /app/app/

# Create necessary directories including matplotlib config
RUN mkdir -p /app/ml/models \
    && mkdir -p /app/logs \
    && mkdir -p /app/data \
    && mkdir -p /tmp/matplotlib \
    && mkdir -p /tmp/fontconfig \
    && chmod 777 /tmp/matplotlib /tmp/fontconfig

# Create non-root user (check if exists first)
RUN groupadd -r mluser || true
RUN useradd -r -g mluser mluser || true
RUN chown -R mluser:mluser /app || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to non-root user
USER mluser

# Expose ML API port
EXPOSE 5000

# Generate initial model if it doesn't exist, then start ML trainer service
CMD ["sh", "-c", "python ml/training/generate_initial_model.py && python ml/training/auto_trainer.py"]
