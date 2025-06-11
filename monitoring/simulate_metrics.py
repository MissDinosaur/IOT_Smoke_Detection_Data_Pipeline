import time
import random
from metrics import (
    start_metrics_server,
    update_sensor_metrics,
    record_processing_time
)

def generate_synthetic_data():
    """Generate synthetic sensor data similar to Kafka producer"""
    return {
        'Temperature[C]': random.uniform(-20, 50),
        'Humidity[%]': random.uniform(30, 70),
        'TVOC[ppb]': random.uniform(0, 15000),
        'eCO2[ppm]': random.uniform(400, 3000),
        'Pressure[hPa]': random.uniform(937, 940),
        'PM1.0': random.uniform(0, 2000),
        'PM2.5': random.uniform(0, 4000),
        'Fire Alarm': str(random.choice([0, 1]))  # Randomly simulate fire alarms
    }

def main():
    print("Starting metrics simulation server...")
    # Start the metrics server on port 8000
    start_metrics_server(port=8000)
    
    row_count = 0
    while True:
        try:
            # Generate synthetic data
            data = generate_synthetic_data()
            row_count += 1
            
            # Simulate processing time
            with record_processing_time('data_processing'):
                # Update all metrics
                update_sensor_metrics(data)
                
            # Print status
            print(f"Generated {row_count}th row data: {data}")
            
            # Wait for 2 seconds before next update
            time.sleep(2)
            
        except Exception as e:
            print(f"Error generating metrics: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main() 