"""
Comprehensive test cases for ML inference module.

This module tests all aspects of the ML inference system including:
- Model loading and management
- Single and batch predictions
- Input validation and preprocessing
- API endpoints and responses
- Error handling and edge cases
- Performance and reliability
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import pickle
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Import the modules to test
import sys
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from ml.inference.model_loader import (
    SmokeDetectionModelLoader,
    get_model_loader,
    load_model
)
from ml.inference.predict import (
    SmokeDetectionPredictor,
    create_sample_data,
    create_fire_scenario_data
)
from ml.inference.predict_wrapper import (
    create_app,
    initialize_predictor
)


class TestSmokeDetectionModelLoader:
    """Test cases for model loading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple trained model for testing
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.scaler = StandardScaler()
        
        # Create sample training data
        np.random.seed(42)
        self.sample_X = np.random.randn(100, 13)  # 13 features
        self.sample_y = np.random.randint(0, 2, 100)
        
        # Fit the model and scaler
        self.model.fit(self.sample_X, self.sample_y)
        self.scaler.fit(self.sample_X)
        
        # Feature columns
        self.feature_columns = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5", "CNT"
        ]
        
        # Create temporary model file
        self.model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_columns": self.feature_columns,
            "metadata": {
                "model_type": "RandomForestClassifier",
                "training_date": "2024-01-01",
                "version": "1.0"
            }
        }
        
        self.temp_model_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        with open(self.temp_model_file.name, 'wb') as f:
            pickle.dump(self.model_data, f)
        self.temp_model_file.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_model_file.name).unlink()
    
    def test_model_loader_initialization(self):
        """Test model loader initialization."""
        loader = SmokeDetectionModelLoader()
        
        assert loader.model is None
        assert loader.scaler is None
        assert loader.feature_columns == []
        assert loader.metadata == {}
        assert loader.is_loaded is False
    
    def test_load_model_success(self):
        """Test successful model loading."""
        loader = SmokeDetectionModelLoader()
        success = loader.load_model(self.temp_model_file.name)
        
        assert success is True
        assert loader.is_loaded is True
        assert loader.model is not None
        assert loader.scaler is not None
        assert len(loader.feature_columns) == 13
        assert "model_type" in loader.metadata
    
    def test_load_model_file_not_found(self):
        """Test model loading with non-existent file."""
        loader = SmokeDetectionModelLoader()
        success = loader.load_model("non_existent_file.pkl")
        
        assert success is False
        assert loader.is_loaded is False
    
    def test_load_model_invalid_format(self):
        """Test model loading with invalid file format."""
        # Create invalid model file
        invalid_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        with open(invalid_file.name, 'wb') as f:
            pickle.dump({"invalid": "data"}, f)
        invalid_file.close()
        
        loader = SmokeDetectionModelLoader()
        success = loader.load_model(invalid_file.name)
        
        assert success is False
        assert loader.is_loaded is False
        
        # Clean up
        Path(invalid_file.name).unlink()
    
    def test_prepare_features_complete_data(self):
        """Test feature preparation with complete data."""
        loader = SmokeDetectionModelLoader()
        loader.load_model(self.temp_model_file.name)
        
        sensor_data = {
            "Temperature[C]": 25.0,
            "Humidity[%]": 50.0,
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
            "CNT": 50
        }
        
        X = loader.prepare_features(sensor_data)
        
        assert X.shape == (1, 13)
        assert isinstance(X, np.ndarray)
    
    def test_prepare_features_missing_data(self):
        """Test feature preparation with missing data."""
        loader = SmokeDetectionModelLoader()
        loader.load_model(self.temp_model_file.name)
        
        incomplete_data = {
            "Temperature[C]": 25.0,
            "Humidity[%]": 50.0
            # Missing other features
        }
        
        X = loader.prepare_features(incomplete_data)
        
        # Should still return proper shape with defaults
        assert X.shape == (1, 13)
    
    def test_validate_input_valid_data(self):
        """Test input validation with valid data."""
        loader = SmokeDetectionModelLoader()
        loader.load_model(self.temp_model_file.name)
        
        valid_data = {
            "Temperature[C]": 25.0,
            "Humidity[%]": 50.0,
            "TVOC[ppb]": 150.0
        }
        
        is_valid, errors = loader.validate_input(valid_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_input_invalid_data(self):
        """Test input validation with invalid data."""
        loader = SmokeDetectionModelLoader()
        loader.load_model(self.temp_model_file.name)
        
        invalid_data = {
            "Temperature[C]": "invalid_value",
            "Humidity[%]": -50.0  # Out of range
        }
        
        is_valid, errors = loader.validate_input(invalid_data)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_get_model_info(self):
        """Test getting model information."""
        loader = SmokeDetectionModelLoader()
        loader.load_model(self.temp_model_file.name)
        
        info = loader.get_model_info()
        
        assert "model_type" in info
        assert "feature_count" in info
        assert "is_loaded" in info
        assert "metadata" in info
        assert info["is_loaded"] is True
        assert info["feature_count"] == 13
    
    def test_model_loader_factory_functions(self):
        """Test factory functions for model loader."""
        # Test get_model_loader
        loader1 = get_model_loader(self.temp_model_file.name)
        assert loader1.is_loaded is True
        
        # Test load_model
        loader2 = load_model(self.temp_model_file.name)
        assert loader2.is_loaded is True


class TestSmokeDetectionPredictor:
    """Test cases for prediction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create model file (reuse from previous test)
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        np.random.seed(42)
        sample_X = np.random.randn(100, 13)
        sample_y = np.random.randint(0, 2, 100)
        self.model.fit(sample_X, sample_y)
        
        feature_columns = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5", "CNT"
        ]
        
        model_data = {
            "model": self.model,
            "scaler": StandardScaler().fit(sample_X),
            "feature_columns": feature_columns,
            "metadata": {"model_type": "RandomForestClassifier"}
        }
        
        self.temp_model_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        with open(self.temp_model_file.name, 'wb') as f:
            pickle.dump(model_data, f)
        self.temp_model_file.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_model_file.name).unlink()
    
    def test_predictor_initialization(self):
        """Test predictor initialization."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        assert predictor.model_loader.is_loaded is True
        assert predictor.model_loader.model is not None
    
    def test_predict_single_valid_data(self):
        """Test single prediction with valid data."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        sensor_data = create_sample_data()
        result = predictor.predict_single(sensor_data)
        
        assert "prediction" in result
        assert "prediction_label" in result
        assert "probability" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert "model_info" in result
        
        # Check prediction values
        assert result["prediction"] in [0, 1]
        assert result["prediction_label"] in ["No Fire", "Fire Detected"]
        assert 0 <= result["confidence"] <= 1
    
    def test_predict_single_fire_scenario(self):
        """Test single prediction with fire scenario data."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        fire_data = create_fire_scenario_data()
        result = predictor.predict_single(fire_data)
        
        # Should return valid prediction structure
        assert "prediction" in result
        assert "prediction_label" in result
        assert result["prediction"] in [0, 1]
    
    def test_predict_from_json_valid(self):
        """Test prediction from JSON string."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        sensor_data = create_sample_data()
        json_data = json.dumps(sensor_data)
        
        result = predictor.predict_from_json(json_data)
        
        assert "prediction" in result
        assert "prediction_label" in result
    
    def test_predict_from_json_invalid(self):
        """Test prediction from invalid JSON."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        with pytest.raises(ValueError):
            predictor.predict_from_json("invalid json")
    
    def test_predict_from_file_csv(self):
        """Test prediction from CSV file."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        # Create temporary CSV file
        sample_data = pd.DataFrame([create_sample_data(), create_fire_scenario_data()])
        temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        sample_data.to_csv(temp_csv.name, index=False)
        temp_csv.close()
        
        try:
            results = predictor.predict_from_file(temp_csv.name)
            
            assert isinstance(results, list)
            assert len(results) == 2
            
            for result in results:
                assert "prediction" in result
                assert "prediction_label" in result
        finally:
            Path(temp_csv.name).unlink()
    
    def test_predict_batch(self):
        """Test batch prediction functionality."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        batch_data = [create_sample_data(), create_fire_scenario_data()]
        results = predictor.predict_batch(batch_data)
        
        assert isinstance(results, list)
        assert len(results) == 2
        
        for result in results:
            assert "prediction" in result
            assert "prediction_label" in result
    
    def test_get_model_info(self):
        """Test getting model information from predictor."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        info = predictor.get_model_info()
        
        assert "model_type" in info
        assert "feature_count" in info
        assert "is_loaded" in info
        assert info["is_loaded"] is True
    
    def test_prediction_with_missing_data(self):
        """Test prediction with missing sensor data."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        incomplete_data = {
            "Temperature[C]": 25.0,
            "Humidity[%]": 50.0
            # Missing other sensors
        }
        
        # Should handle missing data gracefully
        result = predictor.predict_single(incomplete_data)
        
        assert "prediction" in result
        assert "prediction_label" in result
    
    def test_prediction_error_handling(self):
        """Test error handling in prediction."""
        predictor = SmokeDetectionPredictor(self.temp_model_file.name)
        
        # Test with completely invalid data
        invalid_data = {
            "Temperature[C]": "completely_invalid",
            "Humidity[%]": None
        }
        
        # Should handle errors gracefully
        result = predictor.predict_single(invalid_data)
        
        # Should still return a result (with defaults)
        assert "prediction" in result


class TestSampleDataFunctions:
    """Test cases for sample data creation functions."""
    
    def test_create_sample_data(self):
        """Test sample data creation."""
        sample_data = create_sample_data()
        
        # Check that all required fields are present
        required_fields = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5", "CNT"
        ]
        
        for field in required_fields:
            assert field in sample_data
            assert isinstance(sample_data[field], (int, float))
        
        # Check reasonable ranges
        assert -50 <= sample_data["Temperature[C]"] <= 100
        assert 0 <= sample_data["Humidity[%]"] <= 100
        assert sample_data["TVOC[ppb]"] >= 0
        assert sample_data["eCO2[ppm]"] >= 0
    
    def test_create_fire_scenario_data(self):
        """Test fire scenario data creation."""
        fire_data = create_fire_scenario_data()
        
        # Check that all required fields are present
        required_fields = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5", "CNT"
        ]
        
        for field in required_fields:
            assert field in fire_data
            assert isinstance(fire_data[field], (int, float))
        
        # Fire scenario should have elevated values
        assert fire_data["Temperature[C]"] > 40  # High temperature
        assert fire_data["TVOC[ppb]"] > 1000     # High TVOC
        assert fire_data["PM2.5"] > 30           # High particulates
    
    def test_sample_data_consistency(self):
        """Test that sample data functions return consistent structure."""
        sample_data = create_sample_data()
        fire_data = create_fire_scenario_data()
        
        # Should have same keys
        assert set(sample_data.keys()) == set(fire_data.keys())
        
        # Should have same data types
        for key in sample_data.keys():
            assert type(sample_data[key]) == type(fire_data[key])


class TestFlaskAPIIntegration:
    """Test cases for Flask API integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create model file for API testing
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        np.random.seed(42)
        sample_X = np.random.randn(100, 13)
        sample_y = np.random.randint(0, 2, 100)
        self.model.fit(sample_X, sample_y)
        
        feature_columns = [
            "Temperature[C]", "Humidity[%]", "TVOC[ppb]", "eCO2[ppm]",
            "Raw H2", "Raw Ethanol", "Pressure[hPa]", "PM1.0", "PM2.5",
            "NC0.5", "NC1.0", "NC2.5", "CNT"
        ]
        
        model_data = {
            "model": self.model,
            "scaler": StandardScaler().fit(sample_X),
            "feature_columns": feature_columns,
            "metadata": {"model_type": "RandomForestClassifier"}
        }
        
        self.temp_model_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        with open(self.temp_model_file.name, 'wb') as f:
            pickle.dump(model_data, f)
        self.temp_model_file.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_model_file.name).unlink()
    
    def test_initialize_predictor(self):
        """Test predictor initialization for Flask app."""
        predictor = initialize_predictor(self.temp_model_file.name)
        
        assert predictor is not None
        assert predictor.model_loader.is_loaded is True
    
    def test_create_flask_app(self):
        """Test Flask app creation."""
        app = create_app(self.temp_model_file.name)
        
        assert app is not None
        assert app.config['TESTING'] is False
    
    def test_flask_app_health_endpoint(self):
        """Test Flask app health endpoint."""
        app = create_app(self.temp_model_file.name)
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            response = client.get('/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert 'model_loaded' in data
    
    def test_flask_app_predict_endpoint(self):
        """Test Flask app prediction endpoint."""
        app = create_app(self.temp_model_file.name)
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test with sample data
            sample_data = create_sample_data()
            response = client.post('/predict', 
                                 data=json.dumps(sample_data),
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'prediction' in data
            assert 'prediction_label' in data
            assert 'confidence' in data
    
    def test_flask_app_sample_endpoint(self):
        """Test Flask app sample prediction endpoint."""
        app = create_app(self.temp_model_file.name)
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            response = client.get('/predict/sample')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'prediction' in data
            assert 'input_data' in data
    
    def test_flask_app_model_info_endpoint(self):
        """Test Flask app model info endpoint."""
        app = create_app(self.temp_model_file.name)
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            response = client.get('/model/info')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'model_type' in data
            assert 'feature_count' in data
            assert 'is_loaded' in data
    
    def test_flask_app_error_handling(self):
        """Test Flask app error handling."""
        app = create_app(self.temp_model_file.name)
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test with invalid JSON
            response = client.post('/predict', 
                                 data='invalid json',
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data


if __name__ == "__main__":
    pytest.main([__file__])
