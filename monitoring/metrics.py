from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# Smoke detection metrics
fire_alarm_counter = Counter(
    'fire_alarm_total',
    'Total number of fire alarms'
)

# Smoke detection reading
smoke_detection_gauge = Gauge(
    'smoke_detection_reading',
    'Current smoke detection reading'
)

# Sensor readings
temperature_gauge = Gauge(
    'temperature_celsius',
    'Current temperature reading in Celsius'
)

humidity_gauge = Gauge(
    'humidity_percent',
    'Current humidity reading in percentage'
)

tvoc_gauge = Gauge(
    'tvoc_ppb',
    'Total Volatile Organic Compounds in ppb'
)

eco2_gauge = Gauge(
    'eco2_ppm',
    'Equivalent CO2 in ppm'
)

pressure_gauge = Gauge(
    'pressure_hpa',
    'Pressure reading in hPa'
)

pm1_gauge = Gauge(
    'pm1_0',
    'PM1.0 particulate matter'
)

pm2_5_gauge = Gauge(
    'pm2_5',
    'PM2.5 particulate matter'
)

processing_time = Histogram(
    'data_processing_seconds',
    'Time spent processing data',
    ['operation']
)

def start_metrics_server(port=8000):
    """Start the Prometheus metrics server"""
    start_http_server(port)

def update_sensor_metrics(data: dict):
    """Update all sensor metrics with new data"""
    # Update smoke detection reading (using PM2.5 as a proxy for smoke)
    smoke_detection_gauge.set(float(data.get('PM2.5', 0)))
    
    # Update other metrics
    temperature_gauge.set(float(data.get('Temperature[C]', 0)))
    humidity_gauge.set(float(data.get('Humidity[%]', 0)))
    tvoc_gauge.set(float(data.get('TVOC[ppb]', 0)))
    eco2_gauge.set(float(data.get('eCO2[ppm]', 0)))
    pressure_gauge.set(float(data.get('Pressure[hPa]', 0)))
    pm1_gauge.set(float(data.get('PM1.0', 0)))
    pm2_5_gauge.set(float(data.get('PM2.5', 0)))
    
    # Record fire alarm if detected
    if int(data.get('Fire Alarm', 0)) == 1:
        fire_alarm_counter.inc()

def record_processing_time(operation: str):
    """Record the time taken for a processing operation"""
    return processing_time.labels(operation=operation).time() 