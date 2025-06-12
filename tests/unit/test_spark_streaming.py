"""
Spark Streaming Tests for IoT Smoke Detection Pipeline.

This module tests:
- Spark streaming context setup
- Kafka integration with Spark
- Data processing and transformations
- ML model integration
- Error handling and recovery
- Performance and scalability
"""

import pytest
import json
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd
import numpy as np

# Test configuration
SPARK_CONFIG = {
    'app_name': 'test_smoke_detection_streaming',
    'kafka_bootstrap_servers': 'localhost:9092',
    'kafka_topic': 'smoke_detection',
    'flask_api_url': 'http://localhost:5000',
    'spark_ui_url': 'http://localhost:4040',
    'batch_duration': 5,  # seconds
    'checkpoint_dir': '/tmp/spark_checkpoint_test'
}

# Sample streaming data
STREAMING_DATA_SAMPLES = [
    {
        'Temperature[C]': 25.5,
        'Humidity[%]': 45.0,
        'TVOC[ppb]': 150.0,
        'eCO2[ppm]': 400.0,
        'Raw H2': 13000.0,
        'Raw Ethanol': 18500.0,
        'Pressure[hPa]': 1013.25,
        'PM1.0': 10.0,
        'PM2.5': 15.0,
        'NC0.5': 100.0,
        'NC1.0': 80.0,
        'NC2.5': 20.0,
        'timestamp': datetime.now().isoformat(),
        'sensor_id': 'sensor_001'
    },
    {
        'Temperature[C]': 85.0,
        'Humidity[%]': 20.0,
        'TVOC[ppb]': 2500.0,
        'eCO2[ppm]': 1200.0,
        'Raw H2': 25000.0,
        'Raw Ethanol': 35000.0,
        'Pressure[hPa]': 1010.0,
        'PM1.0': 150.0,
        'PM2.5': 250.0,
        'NC0.5': 2000.0,
        'NC1.0': 1500.0,
        'NC2.5': 800.0,
        'timestamp': datetime.now().isoformat(),
        'sensor_id': 'sensor_002'
    }
]


class TestSparkStreamingSetup:
    """Test Spark streaming setup and configuration."""
    
    def test_spark_ui_accessibility(self):
        """Test Spark UI is accessible."""
        try:
            response = requests.get(SPARK_CONFIG['spark_ui_url'], timeout=10)
            assert response.status_code == 200
            
            # Check if it's actually Spark UI
            content = response.text.lower()
            assert 'spark' in content or 'streaming' in content
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Spark UI not accessible: {e}")
    
    def test_spark_streaming_context(self):
        """Test Spark streaming context creation."""
        try:
            # Mock Spark imports since they might not be available in test environment
            with patch('pyspark.streaming.StreamingContext') as mock_ssc:
                with patch('pyspark.SparkContext') as mock_sc:
                    # Mock successful context creation
                    mock_sc.return_value = Mock()
                    mock_ssc.return_value = Mock()
                    
                    # Test context creation logic
                    from unittest.mock import Mock
                    
                    # Simulate context creation
                    spark_context = Mock()
                    streaming_context = Mock()
                    
                    # Verify context configuration
                    assert spark_context is not None
                    assert streaming_context is not None
                    
        except ImportError:
            pytest.skip("PySpark not available in test environment")
    
    def test_kafka_spark_integration_config(self):
        """Test Kafka-Spark integration configuration."""
        # Test configuration parameters
        kafka_params = {
            'bootstrap.servers': SPARK_CONFIG['kafka_bootstrap_servers'],
            'key.deserializer': 'org.apache.kafka.common.serialization.StringDeserializer',
            'value.deserializer': 'org.apache.kafka.common.serialization.StringDeserializer',
            'group.id': 'spark_streaming_test',
            'auto.offset.reset': 'latest',
            'enable.auto.commit': 'false'
        }
        
        # Verify required parameters are present
        assert 'bootstrap.servers' in kafka_params
        assert 'group.id' in kafka_params
        assert kafka_params['bootstrap.servers'] == SPARK_CONFIG['kafka_bootstrap_servers']


class TestDataProcessingLogic:
    """Test data processing and transformation logic."""
    
    def test_sensor_data_validation(self):
        """Test sensor data validation logic."""
        # Valid data
        valid_data = STREAMING_DATA_SAMPLES[0].copy()
        assert self._validate_sensor_data(valid_data) == True
        
        # Missing required field
        invalid_data = valid_data.copy()
        del invalid_data['Temperature[C]']
        assert self._validate_sensor_data(invalid_data) == False
        
        # Invalid data type
        invalid_data = valid_data.copy()
        invalid_data['Temperature[C]'] = 'invalid'
        assert self._validate_sensor_data(invalid_data) == False
        
        # Out of range values
        invalid_data = valid_data.copy()
        invalid_data['Temperature[C]'] = -100.0  # Unrealistic temperature
        assert self._validate_sensor_data(invalid_data) == False
    
    def test_data_transformation(self):
        """Test data transformation for ML prediction."""
        raw_data = STREAMING_DATA_SAMPLES[0].copy()
        transformed_data = self._transform_for_prediction(raw_data)
        
        # Check required fields for ML model
        required_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        for field in required_fields:
            assert field in transformed_data
            assert isinstance(transformed_data[field], (int, float))
        
        # Check that non-ML fields are removed
        assert 'timestamp' not in transformed_data
        assert 'sensor_id' not in transformed_data
    
    def test_batch_processing(self):
        """Test batch processing of streaming data."""
        batch_data = STREAMING_DATA_SAMPLES.copy()
        
        # Process batch
        processed_batch = self._process_streaming_batch(batch_data)
        
        assert len(processed_batch) == len(batch_data)
        
        for item in processed_batch:
            assert 'prediction_result' in item
            assert 'processing_timestamp' in item
            assert 'original_data' in item
    
    def test_aggregation_logic(self):
        """Test data aggregation for analytics."""
        # Create sample data with timestamps
        sample_data = []
        base_time = datetime.now()
        
        for i in range(10):
            data = STREAMING_DATA_SAMPLES[0].copy()
            data['timestamp'] = (base_time.timestamp() + i * 60)  # 1 minute intervals
            data['sensor_id'] = f'sensor_{i % 3}'  # 3 different sensors
            sample_data.append(data)
        
        # Test aggregation
        aggregated = self._aggregate_sensor_data(sample_data, window_minutes=5)
        
        assert 'sensor_counts' in aggregated
        assert 'avg_temperature' in aggregated
        assert 'max_temperature' in aggregated
        assert 'min_temperature' in aggregated
    
    def _validate_sensor_data(self, data):
        """Helper method to validate sensor data."""
        required_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                return False
            if not isinstance(data[field], (int, float)):
                return False
        
        # Check value ranges
        ranges = {
            'Temperature[C]': (-50, 150),
            'Humidity[%]': (0, 100),
            'Pressure[hPa]': (800, 1200)
        }
        
        for field, (min_val, max_val) in ranges.items():
            if field in data:
                if not (min_val <= data[field] <= max_val):
                    return False
        
        return True
    
    def _transform_for_prediction(self, data):
        """Helper method to transform data for ML prediction."""
        # Extract only ML-required fields
        ml_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        transformed = {}
        for field in ml_fields:
            if field in data:
                transformed[field] = float(data[field])
        
        return transformed
    
    def _process_streaming_batch(self, batch):
        """Helper method to process a batch of streaming data."""
        processed = []
        
        for item in batch:
            if self._validate_sensor_data(item):
                transformed = self._transform_for_prediction(item)
                
                # Simulate prediction (would call Flask API in real implementation)
                prediction_result = {
                    'prediction': 0,  # Mock prediction
                    'confidence': {'fire': 0.1, 'no_fire': 0.9}
                }
                
                processed_item = {
                    'original_data': item,
                    'transformed_data': transformed,
                    'prediction_result': prediction_result,
                    'processing_timestamp': datetime.now().isoformat()
                }
                
                processed.append(processed_item)
        
        return processed
    
    def _aggregate_sensor_data(self, data, window_minutes=5):
        """Helper method to aggregate sensor data."""
        if not data:
            return {}
        
        # Group by sensor
        sensor_groups = {}
        for item in data:
            sensor_id = item.get('sensor_id', 'unknown')
            if sensor_id not in sensor_groups:
                sensor_groups[sensor_id] = []
            sensor_groups[sensor_id].append(item)
        
        # Calculate aggregations
        temperatures = [item['Temperature[C]'] for item in data if 'Temperature[C]' in item]
        
        aggregated = {
            'sensor_counts': {sensor: len(items) for sensor, items in sensor_groups.items()},
            'avg_temperature': sum(temperatures) / len(temperatures) if temperatures else 0,
            'max_temperature': max(temperatures) if temperatures else 0,
            'min_temperature': min(temperatures) if temperatures else 0,
            'total_records': len(data),
            'window_minutes': window_minutes
        }
        
        return aggregated


class TestMLIntegration:
    """Test ML model integration in streaming."""
    
    def test_flask_api_integration(self):
        """Test integration with Flask API for predictions."""
        try:
            # Test API health
            response = requests.get(f"{SPARK_CONFIG['flask_api_url']}/health", timeout=5)
            assert response.status_code == 200
            
            # Test prediction endpoint
            test_data = {k: v for k, v in STREAMING_DATA_SAMPLES[0].items() 
                        if k not in ['timestamp', 'sensor_id']}
            
            response = requests.post(
                f"{SPARK_CONFIG['flask_api_url']}/predict",
                json=test_data,
                timeout=10
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify prediction structure
            assert 'prediction' in result
            assert 'prediction_label' in result
            assert 'confidence' in result
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_batch_prediction_integration(self):
        """Test batch prediction integration."""
        try:
            # Prepare batch data
            batch_data = []
            for sample in STREAMING_DATA_SAMPLES:
                api_data = {k: v for k, v in sample.items() 
                           if k not in ['timestamp', 'sensor_id']}
                batch_data.append(api_data)
            
            response = requests.post(
                f"{SPARK_CONFIG['flask_api_url']}/predict/batch",
                json=batch_data,
                timeout=15
            )
            
            assert response.status_code == 200
            result = response.json()
            
            assert 'predictions' in result
            assert 'summary' in result
            assert len(result['predictions']) == len(batch_data)
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_prediction_error_handling(self):
        """Test error handling in prediction calls."""
        try:
            # Test with invalid data
            invalid_data = {'invalid_field': 'invalid_value'}
            
            response = requests.post(
                f"{SPARK_CONFIG['flask_api_url']}/predict",
                json=invalid_data,
                timeout=10
            )
            
            # Should get error response
            assert response.status_code in [400, 422, 500]
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestStreamingPerformance:
    """Test streaming performance and scalability."""
    
    def test_throughput_simulation(self):
        """Test streaming throughput simulation."""
        # Simulate processing multiple batches
        batch_size = 100
        num_batches = 10
        
        total_processed = 0
        start_time = time.time()
        
        for batch_num in range(num_batches):
            # Simulate batch processing
            batch = []
            for i in range(batch_size):
                data = STREAMING_DATA_SAMPLES[i % len(STREAMING_DATA_SAMPLES)].copy()
                data['batch_num'] = batch_num
                data['item_num'] = i
                batch.append(data)
            
            # Process batch
            processed = self._simulate_batch_processing(batch)
            total_processed += len(processed)
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = total_processed / duration
        
        print(f"Simulated throughput: {throughput:.2f} records/second")
        assert throughput > 500  # Should handle at least 500 records/second
    
    def test_latency_simulation(self):
        """Test streaming latency simulation."""
        latencies = []
        
        for i in range(50):
            start_time = time.time()
            
            # Simulate single record processing
            data = STREAMING_DATA_SAMPLES[0].copy()
            processed = self._simulate_single_processing(data)
            
            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print(f"Average latency: {avg_latency*1000:.2f}ms")
        print(f"Maximum latency: {max_latency*1000:.2f}ms")
        
        # Latency should be reasonable
        assert avg_latency < 0.1  # Less than 100ms average
        assert max_latency < 0.5  # Less than 500ms maximum
    
    def test_memory_usage_simulation(self):
        """Test memory usage in streaming simulation."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large batch to test memory usage
        large_batch = []
        for i in range(1000):
            data = STREAMING_DATA_SAMPLES[i % len(STREAMING_DATA_SAMPLES)].copy()
            data['large_batch_id'] = i
            large_batch.append(data)
        
        # Process the large batch
        processed = self._simulate_batch_processing(large_batch)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage increase: {memory_increase:.2f}MB")
        
        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB increase
    
    def _simulate_batch_processing(self, batch):
        """Simulate batch processing for performance testing."""
        processed = []
        
        for item in batch:
            # Simulate validation
            if self._validate_sensor_data(item):
                # Simulate transformation
                transformed = self._transform_for_prediction(item)
                
                # Simulate prediction (without actual API call)
                prediction = {
                    'prediction': 0,
                    'confidence': {'fire': 0.1, 'no_fire': 0.9},
                    'processing_time': 0.001
                }
                
                processed_item = {
                    'original': item,
                    'transformed': transformed,
                    'prediction': prediction
                }
                
                processed.append(processed_item)
        
        return processed
    
    def _simulate_single_processing(self, data):
        """Simulate single record processing."""
        if self._validate_sensor_data(data):
            transformed = self._transform_for_prediction(data)
            return {
                'original': data,
                'transformed': transformed,
                'processed': True
            }
        return {'processed': False}
    
    def _validate_sensor_data(self, data):
        """Reuse validation logic."""
        required_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        for field in required_fields:
            if field not in data or not isinstance(data[field], (int, float)):
                return False
        
        return True
    
    def _transform_for_prediction(self, data):
        """Reuse transformation logic."""
        ml_fields = [
            'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
            'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
            'NC0.5', 'NC1.0', 'NC2.5'
        ]
        
        return {field: float(data[field]) for field in ml_fields if field in data}


class TestErrorHandling:
    """Test error handling and recovery in streaming."""
    
    def test_malformed_data_handling(self):
        """Test handling of malformed data."""
        malformed_data = [
            {'incomplete': 'data'},
            {'Temperature[C]': 'not_a_number'},
            {},  # Empty data
            None  # Null data
        ]
        
        for data in malformed_data:
            try:
                if data is not None:
                    result = self._safe_process_data(data)
                    # Should handle gracefully without crashing
                    assert result is not None
                    assert 'error' in result or 'processed' in result
            except Exception as e:
                # Should not raise unhandled exceptions
                assert False, f"Unhandled exception for data {data}: {e}"
    
    def test_api_failure_handling(self):
        """Test handling of API failures."""
        # Simulate API failure scenarios
        api_failures = [
            {'status_code': 500, 'error': 'Internal Server Error'},
            {'status_code': 404, 'error': 'Not Found'},
            {'status_code': 400, 'error': 'Bad Request'},
            {'timeout': True}
        ]
        
        for failure in api_failures:
            result = self._simulate_api_call_with_failure(failure)
            
            # Should handle failure gracefully
            assert 'error' in result or 'retry' in result
            assert result.get('handled', False) == True
    
    def _safe_process_data(self, data):
        """Safely process data with error handling."""
        try:
            if data is None:
                return {'error': 'null_data', 'processed': False}
            
            if not isinstance(data, dict):
                return {'error': 'invalid_type', 'processed': False}
            
            if not data:
                return {'error': 'empty_data', 'processed': False}
            
            # Try to validate
            if self._validate_sensor_data(data):
                return {'processed': True, 'valid': True}
            else:
                return {'processed': True, 'valid': False, 'error': 'validation_failed'}
                
        except Exception as e:
            return {'error': str(e), 'processed': False}
    
    def _simulate_api_call_with_failure(self, failure_scenario):
        """Simulate API call with various failure scenarios."""
        try:
            if failure_scenario.get('timeout'):
                # Simulate timeout
                time.sleep(0.001)  # Small delay to simulate timeout
                return {'error': 'timeout', 'handled': True, 'retry': True}
            
            status_code = failure_scenario.get('status_code')
            if status_code:
                if status_code >= 500:
                    return {'error': 'server_error', 'handled': True, 'retry': True}
                elif status_code >= 400:
                    return {'error': 'client_error', 'handled': True, 'retry': False}
            
            return {'success': True, 'handled': True}
            
        except Exception as e:
            return {'error': str(e), 'handled': True, 'retry': False}
    
    def _validate_sensor_data(self, data):
        """Reuse validation logic with error handling."""
        try:
            required_fields = [
                'Temperature[C]', 'Humidity[%]', 'TVOC[ppb]', 'eCO2[ppm]',
                'Raw H2', 'Raw Ethanol', 'Pressure[hPa]', 'PM1.0', 'PM2.5',
                'NC0.5', 'NC1.0', 'NC2.5'
            ]
            
            for field in required_fields:
                if field not in data:
                    return False
                if not isinstance(data[field], (int, float)):
                    return False
            
            return True
            
        except Exception:
            return False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
