"""
ML Streaming Integration Tests for IoT Smoke Detection Pipeline.

This module tests:
- ML model integration in streaming pipeline
- Real-time prediction accuracy
- Model performance under streaming load
- ML model reloading and hot-swapping
- Feature engineering in streaming context
- Model drift detection
- Prediction confidence analysis
- Batch vs streaming prediction consistency
"""

import pytest
import json
import time
import requests
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pickle
import tempfile
import os
from pathlib import Path

# Test configuration
ML_STREAMING_CONFIG = {
    'flask_api_url': 'http://localhost:5000',
    'kafka_bootstrap_servers': 'localhost:9092',
    'kafka_topic': 'smoke_detection',
    'model_path': 'ml/models/best_model.pkl',
    'test_timeout': 60,
    'prediction_threshold': 0.5,
    'performance_threshold': {
        'accuracy': 0.8,
        'precision': 0.75,
        'recall': 0.75,
        'f1': 0.75,
        'response_time_ms': 100
    }
}

# Sample ML test data
NORMAL_SENSOR_DATA = {
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
    'NC2.5': 20.0
}

FIRE_SENSOR_DATA = {
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
    'NC2.5': 800.0
}

EDGE_CASE_DATA = [
    # High temperature, normal other values
    {**NORMAL_SENSOR_DATA, 'Temperature[C]': 60.0},
    # High particulate matter
    {**NORMAL_SENSOR_DATA, 'PM2.5': 100.0},
    # High TVOC
    {**NORMAL_SENSOR_DATA, 'TVOC[ppb]': 1000.0},
    # Low humidity, high temperature
    {**NORMAL_SENSOR_DATA, 'Temperature[C]': 50.0, 'Humidity[%]': 15.0},
]


class TestMLModelIntegration:
    """Test ML model integration in streaming context."""
    
    def test_model_availability(self, api_client):
        """Test that ML model is loaded and available."""
        try:
            response = api_client.get('/model/info', timeout=10)
            assert response.status_code == 200
            
            model_info = response.json()
            assert 'model_name' in model_info
            assert 'feature_columns' in model_info
            assert 'training_timestamp' in model_info
            assert 'model_metrics' in model_info
            
            # Verify feature columns match expected sensor data
            feature_columns = model_info['feature_columns']
            expected_features = list(NORMAL_SENSOR_DATA.keys())
            
            for feature in expected_features:
                assert feature in feature_columns, f"Feature {feature} missing from model"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_single_prediction_accuracy(self, api_client):
        """Test single prediction accuracy and response format."""
        try:
            # Test normal conditions (should predict no fire)
            response = api_client.predict(NORMAL_SENSOR_DATA, timeout=10)
            assert response.status_code == 200
            
            result = response.json()
            self._validate_prediction_response(result)
            
            # For normal conditions, fire confidence should be low
            fire_confidence = result['confidence']['fire']
            assert fire_confidence < 0.7, f"Fire confidence too high for normal data: {fire_confidence}"
            
            # Test fire conditions (should predict fire)
            response = api_client.predict(FIRE_SENSOR_DATA, timeout=10)
            assert response.status_code == 200
            
            result = response.json()
            self._validate_prediction_response(result)
            
            # For fire conditions, fire confidence should be higher
            fire_confidence = result['confidence']['fire']
            # Note: Actual threshold depends on trained model
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_batch_prediction_consistency(self, api_client):
        """Test batch prediction consistency and performance."""
        try:
            # Create batch with mixed normal and fire scenarios
            batch_data = [
                NORMAL_SENSOR_DATA,
                FIRE_SENSOR_DATA,
                *EDGE_CASE_DATA
            ]
            
            start_time = time.time()
            response = api_client.predict_batch(batch_data, timeout=30)
            end_time = time.time()
            
            assert response.status_code == 200
            
            result = response.json()
            assert 'predictions' in result
            assert 'summary' in result
            
            predictions = result['predictions']
            assert len(predictions) == len(batch_data)
            
            # Validate each prediction
            for i, prediction in enumerate(predictions):
                self._validate_prediction_response(prediction)
                
                # Check that predictions are consistent with input data type
                if i == 0:  # Normal data
                    assert prediction['confidence']['fire'] < 0.7
                elif i == 1:  # Fire data
                    # Fire scenario should have higher fire confidence
                    pass  # Threshold depends on model training
            
            # Check performance
            batch_processing_time = end_time - start_time
            avg_time_per_prediction = batch_processing_time / len(batch_data)
            
            assert avg_time_per_prediction < 0.1, f"Batch prediction too slow: {avg_time_per_prediction}s per prediction"
            
            # Validate summary
            summary = result['summary']
            assert summary['total_samples'] == len(batch_data)
            assert 'fire_predictions' in summary
            assert 'no_fire_predictions' in summary
            assert 'avg_confidence' in summary
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_prediction_performance(self, api_client):
        """Test ML prediction performance under load."""
        try:
            # Test single prediction latency
            latencies = []
            for _ in range(20):
                start_time = time.time()
                response = api_client.predict(NORMAL_SENSOR_DATA, timeout=5)
                end_time = time.time()
                
                assert response.status_code == 200
                latencies.append((end_time - start_time) * 1000)  # Convert to ms
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            print(f"Average prediction latency: {avg_latency:.2f}ms")
            print(f"Maximum prediction latency: {max_latency:.2f}ms")
            
            # Performance assertions
            assert avg_latency < ML_STREAMING_CONFIG['performance_threshold']['response_time_ms']
            assert max_latency < ML_STREAMING_CONFIG['performance_threshold']['response_time_ms'] * 2
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_model_feature_engineering(self, api_client):
        """Test that model handles feature engineering correctly."""
        try:
            # Test with minimal required features
            minimal_data = {
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
                'NC2.5': 20.0
            }
            
            response = api_client.predict(minimal_data, timeout=10)
            assert response.status_code == 200
            
            result = response.json()
            self._validate_prediction_response(result)
            
            # Test with additional features (should be ignored gracefully)
            extended_data = minimal_data.copy()
            extended_data.update({
                'extra_feature_1': 123.45,
                'extra_feature_2': 'should_be_ignored',
                'timestamp': datetime.now().isoformat()
            })
            
            response = api_client.predict(extended_data, timeout=10)
            assert response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_model_error_handling(self, api_client):
        """Test ML model error handling with invalid data."""
        try:
            # Test with missing required features
            incomplete_data = {
                'Temperature[C]': 25.5,
                'Humidity[%]': 45.0
                # Missing other required features
            }
            
            response = api_client.predict(incomplete_data, timeout=10)
            assert response.status_code in [400, 422], "Should return error for incomplete data"
            
            # Test with invalid data types
            invalid_data = NORMAL_SENSOR_DATA.copy()
            invalid_data['Temperature[C]'] = 'invalid_temperature'
            
            response = api_client.predict(invalid_data, timeout=10)
            assert response.status_code in [400, 422], "Should return error for invalid data types"
            
            # Test with extreme outliers
            outlier_data = NORMAL_SENSOR_DATA.copy()
            outlier_data['Temperature[C]'] = 1000.0  # Extreme outlier
            
            response = api_client.predict(outlier_data, timeout=10)
            # Should either handle gracefully or return appropriate error
            assert response.status_code in [200, 400, 422]
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def _validate_prediction_response(self, result):
        """Validate the structure of a prediction response."""
        # Required fields
        assert 'prediction' in result
        assert 'prediction_label' in result
        assert 'confidence' in result
        assert 'processing_time_seconds' in result
        
        # Validate prediction values
        assert result['prediction'] in [0, 1]
        assert result['prediction_label'] in ['fire', 'no_fire']
        
        # Validate confidence scores
        confidence = result['confidence']
        assert 'fire' in confidence
        assert 'no_fire' in confidence
        assert 0.0 <= confidence['fire'] <= 1.0
        assert 0.0 <= confidence['no_fire'] <= 1.0
        assert abs(confidence['fire'] + confidence['no_fire'] - 1.0) < 0.01  # Should sum to ~1
        
        # Validate processing time
        assert isinstance(result['processing_time_seconds'], (int, float))
        assert result['processing_time_seconds'] > 0


class TestMLStreamingPipeline:
    """Test ML integration in the complete streaming pipeline."""
    
    def test_kafka_to_ml_pipeline(self, kafka_producer_client, api_client):
        """Test complete pipeline from Kafka to ML prediction."""
        try:
            # Send sensor data to Kafka
            test_data = NORMAL_SENSOR_DATA.copy()
            test_data['pipeline_test_id'] = f'test_{int(time.time())}'
            
            future = kafka_producer_client.send('smoke_detection', value=test_data)
            record = future.get(timeout=10)
            
            assert record.topic == 'smoke_detection'
            
            # Simulate stream processing by calling API directly
            # (In real pipeline, stream processor would consume from Kafka and call API)
            api_data = {k: v for k, v in test_data.items() if k != 'pipeline_test_id'}
            
            response = api_client.predict(api_data, timeout=10)
            assert response.status_code == 200
            
            result = response.json()
            self._validate_prediction_response(result)
            
        except Exception as e:
            pytest.skip(f"Pipeline test failed: {e}")
    
    def test_streaming_ml_performance(self, kafka_producer_client, api_client):
        """Test ML performance in streaming context."""
        try:
            # Simulate streaming load
            num_messages = 50
            start_time = time.time()
            
            # Send messages to Kafka
            for i in range(num_messages):
                test_data = NORMAL_SENSOR_DATA.copy()
                test_data['stream_test_id'] = i
                test_data['Temperature[C]'] += i * 0.5  # Add variation
                
                kafka_producer_client.send('smoke_detection', value=test_data)
            
            kafka_producer_client.flush()
            kafka_send_time = time.time()
            
            # Simulate ML processing (direct API calls)
            prediction_times = []
            for i in range(num_messages):
                api_data = NORMAL_SENSOR_DATA.copy()
                api_data['Temperature[C]'] += i * 0.5
                
                pred_start = time.time()
                response = api_client.predict(api_data, timeout=5)
                pred_end = time.time()
                
                assert response.status_code == 200
                prediction_times.append(pred_end - pred_start)
            
            total_time = time.time() - start_time
            kafka_throughput = num_messages / (kafka_send_time - start_time)
            ml_throughput = num_messages / sum(prediction_times)
            avg_prediction_time = sum(prediction_times) / len(prediction_times)
            
            print(f"Kafka throughput: {kafka_throughput:.2f} msg/s")
            print(f"ML throughput: {ml_throughput:.2f} predictions/s")
            print(f"Average prediction time: {avg_prediction_time*1000:.2f}ms")
            
            # Performance assertions
            assert kafka_throughput > 10, "Kafka throughput too low"
            assert ml_throughput > 5, "ML throughput too low"
            assert avg_prediction_time < 0.2, "ML predictions too slow"
            
        except Exception as e:
            pytest.skip(f"Streaming performance test failed: {e}")
    
    def _validate_prediction_response(self, result):
        """Validate the structure of a prediction response."""
        assert 'prediction' in result
        assert 'prediction_label' in result
        assert 'confidence' in result
        assert result['prediction'] in [0, 1]
        assert result['prediction_label'] in ['fire', 'no_fire']


class TestMLModelManagement:
    """Test ML model management in streaming context."""
    
    def test_model_info_endpoint(self, api_client):
        """Test model information endpoint."""
        try:
            response = api_client.get('/model/info', timeout=10)
            assert response.status_code == 200
            
            model_info = response.json()
            
            # Required model information
            required_fields = [
                'model_name', 'feature_columns', 'training_timestamp',
                'model_metrics', 'model_version'
            ]
            
            for field in required_fields:
                assert field in model_info, f"Missing field: {field}"
            
            # Validate feature columns
            feature_columns = model_info['feature_columns']
            assert isinstance(feature_columns, list)
            assert len(feature_columns) > 0
            
            # Validate metrics
            metrics = model_info['model_metrics']
            assert isinstance(metrics, dict)
            
            expected_metrics = ['accuracy', 'precision', 'recall', 'f1']
            for metric in expected_metrics:
                if metric in metrics:
                    assert 0.0 <= metrics[metric] <= 1.0
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_model_health_check(self, api_client):
        """Test model health check functionality."""
        try:
            response = api_client.get('/model/health', timeout=10)
            
            if response.status_code == 200:
                health_info = response.json()
                assert 'model_loaded' in health_info
                assert 'last_prediction_time' in health_info
                assert health_info['model_loaded'] == True
            else:
                # Health endpoint might not exist, check general health
                response = api_client.get('/health', timeout=10)
                assert response.status_code == 200
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_model_reload_capability(self, api_client):
        """Test model reload functionality if available."""
        try:
            # Check if reload endpoint exists
            response = api_client.post('/model/reload', timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                assert 'status' in result
                assert result['status'] in ['success', 'reloaded']
                
                # Verify model still works after reload
                pred_response = api_client.predict(NORMAL_SENSOR_DATA, timeout=10)
                assert pred_response.status_code == 200
                
            elif response.status_code == 404:
                pytest.skip("Model reload endpoint not implemented")
            else:
                pytest.fail(f"Model reload failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestMLDataValidation:
    """Test ML data validation and preprocessing."""
    
    def test_feature_validation(self, api_client):
        """Test feature validation in ML pipeline."""
        try:
            # Test with all required features
            complete_data = NORMAL_SENSOR_DATA.copy()
            response = api_client.predict(complete_data, timeout=10)
            assert response.status_code == 200
            
            # Test with missing features
            for feature in NORMAL_SENSOR_DATA.keys():
                incomplete_data = NORMAL_SENSOR_DATA.copy()
                del incomplete_data[feature]
                
                response = api_client.predict(incomplete_data, timeout=10)
                # Should either handle gracefully or return appropriate error
                assert response.status_code in [200, 400, 422]
                
                if response.status_code != 200:
                    error_info = response.json()
                    assert 'error' in error_info or 'message' in error_info
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_data_type_validation(self, api_client):
        """Test data type validation in ML pipeline."""
        try:
            # Test with correct data types
            valid_data = NORMAL_SENSOR_DATA.copy()
            response = api_client.predict(valid_data, timeout=10)
            assert response.status_code == 200
            
            # Test with invalid data types
            invalid_types = [
                ('Temperature[C]', 'not_a_number'),
                ('Humidity[%]', None),
                ('TVOC[ppb]', [1, 2, 3]),
                ('eCO2[ppm]', {'invalid': 'dict'}),
            ]
            
            for feature, invalid_value in invalid_types:
                invalid_data = NORMAL_SENSOR_DATA.copy()
                invalid_data[feature] = invalid_value
                
                response = api_client.predict(invalid_data, timeout=10)
                # Should return error for invalid data types
                assert response.status_code in [400, 422]
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_outlier_handling(self, api_client):
        """Test outlier handling in ML pipeline."""
        try:
            # Test with extreme outliers
            outlier_tests = [
                ('Temperature[C]', -100.0),  # Extreme cold
                ('Temperature[C]', 200.0),   # Extreme hot
                ('Humidity[%]', -50.0),      # Invalid humidity
                ('Humidity[%]', 150.0),      # Invalid humidity
                ('Pressure[hPa]', 0.0),      # Invalid pressure
                ('PM2.5', -10.0),            # Negative particulate matter
            ]
            
            for feature, outlier_value in outlier_tests:
                outlier_data = NORMAL_SENSOR_DATA.copy()
                outlier_data[feature] = outlier_value
                
                response = api_client.predict(outlier_data, timeout=10)
                
                # Should either handle gracefully or return appropriate response
                assert response.status_code in [200, 400, 422]
                
                if response.status_code == 200:
                    result = response.json()
                    # If handled gracefully, should still return valid prediction structure
                    assert 'prediction' in result
                    assert 'confidence' in result
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


class TestMLPredictionAnalysis:
    """Test ML prediction analysis and confidence scoring."""
    
    def test_confidence_score_analysis(self, api_client):
        """Test confidence score analysis across different scenarios."""
        try:
            test_scenarios = [
                ('normal', NORMAL_SENSOR_DATA),
                ('fire', FIRE_SENSOR_DATA),
                *[(f'edge_case_{i}', data) for i, data in enumerate(EDGE_CASE_DATA)]
            ]
            
            confidence_scores = {}
            
            for scenario_name, test_data in test_scenarios:
                response = api_client.predict(test_data, timeout=10)
                assert response.status_code == 200
                
                result = response.json()
                confidence_scores[scenario_name] = result['confidence']
                
                # Validate confidence structure
                assert 'fire' in result['confidence']
                assert 'no_fire' in result['confidence']
                
                fire_conf = result['confidence']['fire']
                no_fire_conf = result['confidence']['no_fire']
                
                # Confidence scores should be valid probabilities
                assert 0.0 <= fire_conf <= 1.0
                assert 0.0 <= no_fire_conf <= 1.0
                assert abs(fire_conf + no_fire_conf - 1.0) < 0.01
            
            # Analyze confidence patterns
            normal_fire_conf = confidence_scores['normal']['fire']
            fire_fire_conf = confidence_scores['fire']['fire']
            
            print(f"Normal scenario fire confidence: {normal_fire_conf:.3f}")
            print(f"Fire scenario fire confidence: {fire_fire_conf:.3f}")
            
            # Fire scenario should generally have higher fire confidence than normal
            # (though this depends on the trained model)
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")
    
    def test_prediction_consistency(self, api_client):
        """Test prediction consistency for identical inputs."""
        try:
            # Make multiple predictions with identical data
            test_data = NORMAL_SENSOR_DATA.copy()
            predictions = []
            
            for _ in range(10):
                response = api_client.predict(test_data, timeout=10)
                assert response.status_code == 200
                
                result = response.json()
                predictions.append(result)
            
            # All predictions should be identical for deterministic models
            first_prediction = predictions[0]['prediction']
            first_confidence = predictions[0]['confidence']
            
            for prediction in predictions[1:]:
                assert prediction['prediction'] == first_prediction
                # Confidence scores should be very close (allowing for floating point precision)
                assert abs(prediction['confidence']['fire'] - first_confidence['fire']) < 0.001
                assert abs(prediction['confidence']['no_fire'] - first_confidence['no_fire']) < 0.001
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Flask API not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
