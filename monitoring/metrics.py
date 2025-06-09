from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# Smoke detection metrics
smoke_detection_counter = Counter(
    'smoke_detection_total',
    'Total number of smoke detections',
    ['sensor_id', 'severity']
)

smoke_level_gauge = Gauge(
    'smoke_level',
    'Current smoke level reading',
    ['sensor_id']
)

sensor_temperature = Gauge(
    'sensor_temperature',
    'Current temperature reading',
    ['sensor_id']
)

sensor_humidity = Gauge(
    'sensor_humidity',
    'Current humidity reading',
    ['sensor_id']
)

processing_time = Histogram(
    'data_processing_seconds',
    'Time spent processing data',
    ['operation']
)

 def start_metrics_server(port=8000):
    """Start the Prometheus metrics server"""
    start_http_server(port)

def record_smoke_detection(sensor_id: str, severity: str):
    """Record a smoke detection event"""
    smoke_detection_counter.labels(sensor_id=sensor_id, severity=severity).inc()

def update_smoke_level(sensor_id: str, level: float):
    """Update the current smoke level reading"""
    smoke_level_gauge.labels(sensor_id=sensor_id).set(level)

def update_temperature(sensor_id: str, temperature: float):
    """Update the current temperature reading"""
    sensor_temperature.labels(sensor_id=sensor_id).set(temperature)

def update_humidity(sensor_id: str, humidity: float):
    """Update the current humidity reading"""
    sensor_humidity.labels(sensor_id=sensor_id).set(humidity)

def record_processing_time(operation: str):
    """Record the time taken for a processing operation"""
    return processing_time.labels(operation=operation).time() 

# Here's an example of how to use the metrics in our data processing code
# Start the metrics server
start_metrics_server(port=8000)

# In your data processing code:
def process_sensor_data(sensor_id: str, data: dict):
    with record_processing_time('process_sensor_data'):
        # Update metrics
        update_smoke_level(sensor_id, data['smoke_level'])
        update_temperature(sensor_id, data['temperature'])
        update_humidity(sensor_id, data['humidity'])
        
        # Record smoke detection if smoke level is high
        if data['smoke_level'] > threshold:
            record_smoke_detection(sensor_id, 'high') 