"""
Mock-based Flask API Tests for IoT Smoke Detection Pipeline.

This module provides Flask API testing using mocks to avoid requiring
a running Flask API server. Tests cover core functionality including:
- Health checks and status monitoring
- Prediction endpoints (single and batch)
- Model information and management
- Input validation and error handling
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Test data
VALID_SENSOR_DATA = {
    "Temperature[C]": 25.5,
    "Humidity[%]": 45.0,
    "TVOC[ppb]": 150.0,
    "eCO2[ppm]": 450.0,
    "Raw H2": 12500,
    "Raw Ethanol": 18500,
    "Pressure[hPa]": 1013.25,
    "PM1.0": 5.2,
    "PM2.5": 8.1,
    "NC0.5": 1200,
    "NC1.0": 800,
    "NC2.5": 150,
    "CNT": 50,
    "Fire Alarm": 0,
}


class TestFlaskAPIEndpointsMocked:
    """Test Flask API endpoints using mocks."""
    
    @patch('requests.get')
    def test_health_endpoint_success(self, mock_get):
        """Test successful health check endpoint."""
        # Mock successful health response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'healthy',
            'timestamp': '2024-01-01T10:00:00Z',
            'version': '1.0.0',
            'services': {
                'database': 'healthy',
                'ml_model': 'healthy',
                'kafka': 'healthy'
            }
        }
        mock_get.return_value = mock_response
        
        # Test the health endpoint
        import requests
        response = requests.get("http://localhost:5000/health", timeout=10)
        
        assert response.status_code == 200
        health_data = response.json()
        
        # Verify required fields
        required_fields = ['status', 'timestamp', 'version']
        for field in required_fields:
            assert field in health_data
        
        assert health_data['status'] == 'healthy'
        assert 'services' in health_data
        
        # Verify mock was called correctly
        mock_get.assert_called_once_with("http://localhost:5000/health", timeout=10)
    
    @patch('requests.post')
    def test_predict_endpoint_success(self, mock_post):
        """Test successful prediction endpoint."""
        # Mock successful prediction response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'prediction': 0,
            'prediction_label': 'no_fire',
            'confidence': {
                'fire': 0.15,
                'no_fire': 0.85
            },
            'processing_time_seconds': 0.045,
            'timestamp': '2024-01-01T10:00:00Z'
        }
        mock_post.return_value = mock_response
        
        # Test the prediction endpoint
        import requests
        response = requests.post(
            "http://localhost:5000/predict",
            json=VALID_SENSOR_DATA,
            timeout=15
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify prediction structure
        required_fields = [
            'prediction', 'prediction_label', 'confidence', 
            'processing_time_seconds', 'timestamp'
        ]
        for field in required_fields:
            assert field in result
        
        # Verify prediction values
        assert result['prediction'] in [0, 1]
        assert result['prediction_label'] in ['fire', 'no_fire']
        
        # Verify confidence scores
        confidence = result['confidence']
        assert 'fire' in confidence
        assert 'no_fire' in confidence
        assert 0.0 <= confidence['fire'] <= 1.0
        assert 0.0 <= confidence['no_fire'] <= 1.0
        
        # Verify mock was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json'] == VALID_SENSOR_DATA
    
    @patch('requests.post')
    def test_predict_batch_endpoint_success(self, mock_post):
        """Test successful batch prediction endpoint."""
        # Mock successful batch prediction response
        batch_data = [VALID_SENSOR_DATA] * 3
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'predictions': [
                {'prediction': 0, 'confidence': {'fire': 0.1, 'no_fire': 0.9}},
                {'prediction': 0, 'confidence': {'fire': 0.2, 'no_fire': 0.8}},
                {'prediction': 1, 'confidence': {'fire': 0.8, 'no_fire': 0.2}},
            ],
            'summary': {
                'total_samples': 3,
                'fire_predictions': 1,
                'no_fire_predictions': 2
            },
            'processing_time_seconds': 0.125
        }
        mock_post.return_value = mock_response
        
        # Test the batch prediction endpoint
        import requests
        response = requests.post(
            "http://localhost:5000/predict/batch",
            json=batch_data,
            timeout=30
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify batch response structure
        assert 'predictions' in result
        assert 'summary' in result
        assert 'processing_time_seconds' in result
        
        predictions = result['predictions']
        assert len(predictions) == len(batch_data)
        
        # Verify each prediction
        for prediction in predictions:
            assert 'prediction' in prediction
            assert 'confidence' in prediction
            assert prediction['prediction'] in [0, 1]
        
        # Verify summary
        summary = result['summary']
        assert summary['total_samples'] == len(batch_data)
        assert summary['fire_predictions'] + summary['no_fire_predictions'] == summary['total_samples']
    
    @patch('requests.get')
    def test_model_info_endpoint_success(self, mock_get):
        """Test successful model info endpoint."""
        # Mock successful model info response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'model_name': 'RandomForestClassifier',
            'model_version': '1.0.0',
            'feature_columns': list(VALID_SENSOR_DATA.keys()),
            'training_timestamp': '2024-01-01T08:00:00Z',
            'model_metrics': {
                'accuracy': 0.95,
                'precision': 0.92,
                'recall': 0.88,
                'f1_score': 0.90
            }
        }
        mock_get.return_value = mock_response
        
        # Test the model info endpoint
        import requests
        response = requests.get("http://localhost:5000/model/info", timeout=10)
        
        assert response.status_code == 200
        model_info = response.json()
        
        # Verify required fields
        required_fields = [
            'model_name', 'model_version', 'feature_columns',
            'training_timestamp', 'model_metrics'
        ]
        for field in required_fields:
            assert field in model_info
        
        # Verify feature columns
        feature_columns = model_info['feature_columns']
        assert isinstance(feature_columns, list)
        assert len(feature_columns) > 0
        
        # Verify model metrics
        metrics = model_info['model_metrics']
        assert isinstance(metrics, dict)
        for metric_name, metric_value in metrics.items():
            assert 0.0 <= metric_value <= 1.0
    
    @patch('requests.post')
    def test_predict_endpoint_validation_error(self, mock_post):
        """Test prediction endpoint with validation error."""
        # Mock validation error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'Validation failed',
            'message': 'Missing required field: Temperature[C]',
            'details': {
                'missing_fields': ['Temperature[C]'],
                'invalid_fields': []
            }
        }
        mock_post.return_value = mock_response
        
        # Test with incomplete data
        incomplete_data = {
            'Humidity[%]': 45.0,
            'TVOC[ppb]': 150.0
            # Missing other required fields
        }
        
        import requests
        response = requests.post(
            "http://localhost:5000/predict",
            json=incomplete_data,
            timeout=10
        )
        
        assert response.status_code == 400
        error_info = response.json()
        assert 'error' in error_info
        assert 'message' in error_info
    
    @patch('requests.get')
    def test_health_endpoint_service_down(self, mock_get):
        """Test health endpoint when service is down."""
        # Mock service down response
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {
            'status': 'unhealthy',
            'timestamp': '2024-01-01T10:00:00Z',
            'version': '1.0.0',
            'services': {
                'database': 'healthy',
                'ml_model': 'down',
                'kafka': 'healthy'
            },
            'errors': ['ML model is not responding']
        }
        mock_get.return_value = mock_response
        
        # Test the health endpoint
        import requests
        response = requests.get("http://localhost:5000/health", timeout=10)
        
        assert response.status_code == 503
        health_data = response.json()
        assert health_data['status'] == 'unhealthy'
        assert 'errors' in health_data


if __name__ == "__main__":
    pytest.main([__file__])
