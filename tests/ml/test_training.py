"""
Comprehensive test cases for ML training module.

This module tests all aspects of the ML training pipeline including:
- Model training and evaluation
- Feature engineering
- Hyperparameter tuning
- Model persistence
- Configuration management
- Error handling
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Import the modules to test
import sys
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from ml.training.train_model import (
    SmokeDetectionTrainer,
    FeatureEngineer,
    ModelConfig,
    TrainingConfig,
    FeatureEngineeringConfig,
    train_smoke_detection_model,
    DEFAULT_MODEL_CONFIGS
)


class TestFeatureEngineer:
    """Test cases for feature engineering functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.feature_engineer = FeatureEngineer()
        
        # Create sample sensor data
        self.sample_data = pd.DataFrame({
            "Temperature[C]": [25.0, 30.0, 35.0, 40.0, 45.0],
            "Humidity[%]": [50.0, 45.0, 40.0, 35.0, 30.0],
            "TVOC[ppb]": [100.0, 150.0, 200.0, 250.0, 300.0],
            "eCO2[ppm]": [400.0, 450.0, 500.0, 550.0, 600.0],
            "Raw H2": [10000, 12000, 14000, 16000, 18000],
            "Raw Ethanol": [15000, 17000, 19000, 21000, 23000],
            "Pressure[hPa]": [1013.25, 1012.0, 1011.0, 1010.0, 1009.0],
            "PM1.0": [5.0, 7.0, 9.0, 11.0, 13.0],
            "PM2.5": [8.0, 10.0, 12.0, 14.0, 16.0]
        })
    
    def test_feature_engineer_initialization(self):
        """Test feature engineer initialization."""
        assert isinstance(self.feature_engineer.config, FeatureEngineeringConfig)
        assert len(self.feature_engineer.created_features) == 0
    
    def test_create_advanced_features_basic(self):
        """Test basic advanced feature creation."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Should have more columns than original
        assert enhanced_data.shape[1] > self.sample_data.shape[1]
        
        # Should preserve original columns
        for col in self.sample_data.columns:
            assert col in enhanced_data.columns
        
        # Check that new features were created
        assert len(self.feature_engineer.created_features) > 0
    
    def test_temperature_based_features(self):
        """Test temperature-based feature creation."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Check temperature-based features
        assert "temp_squared" in enhanced_data.columns
        assert "temp_log" in enhanced_data.columns
        
        # Verify calculations
        expected_temp_squared = self.sample_data["Temperature[C]"] ** 2
        pd.testing.assert_series_equal(
            enhanced_data["temp_squared"], 
            expected_temp_squared, 
            check_names=False
        )
    
    def test_humidity_based_features(self):
        """Test humidity-based feature creation."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Check humidity-based features
        assert "humidity_squared" in enhanced_data.columns
        assert "humidity_log" in enhanced_data.columns
        
        # Verify calculations
        expected_humidity_squared = self.sample_data["Humidity[%]"] ** 2
        pd.testing.assert_series_equal(
            enhanced_data["humidity_squared"], 
            expected_humidity_squared, 
            check_names=False
        )
    
    def test_air_quality_ratio_features(self):
        """Test air quality ratio feature creation."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Check air quality ratio
        assert "tvoc_eco2_ratio" in enhanced_data.columns
        
        # Verify calculation (with small epsilon to avoid division by zero)
        expected_ratio = self.sample_data["TVOC[ppb]"] / (self.sample_data["eCO2[ppm]"] + 1e-5)
        np.testing.assert_array_almost_equal(
            enhanced_data["tvoc_eco2_ratio"].values,
            expected_ratio.values,
            decimal=5
        )
    
    def test_particulate_matter_features(self):
        """Test particulate matter feature creation."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Check PM features
        assert "pm_ratio" in enhanced_data.columns
        assert "pm_sum" in enhanced_data.columns
        
        # Verify calculations
        expected_pm_sum = self.sample_data["PM1.0"] + self.sample_data["PM2.5"]
        pd.testing.assert_series_equal(
            enhanced_data["pm_sum"], 
            expected_pm_sum, 
            check_names=False
        )
    
    def test_interaction_features(self):
        """Test interaction feature creation."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Check interaction features
        assert "temp_humidity_interaction" in enhanced_data.columns
        assert "heat_index" in enhanced_data.columns
        
        # Verify interaction calculation
        expected_interaction = self.sample_data["Temperature[C]"] * self.sample_data["Humidity[%]"]
        pd.testing.assert_series_equal(
            enhanced_data["temp_humidity_interaction"], 
            expected_interaction, 
            check_names=False
        )
    
    def test_gas_sensor_features(self):
        """Test gas sensor combination features."""
        enhanced_data = self.feature_engineer.create_advanced_features(self.sample_data)
        
        # Check gas sensor features
        assert "gas_sensor_ratio" in enhanced_data.columns
        assert "gas_sensor_sum" in enhanced_data.columns
        
        # Verify sum calculation
        expected_gas_sum = self.sample_data["Raw H2"] + self.sample_data["Raw Ethanol"]
        pd.testing.assert_series_equal(
            enhanced_data["gas_sensor_sum"], 
            expected_gas_sum, 
            check_names=False
        )
    
    def test_missing_columns_handling(self):
        """Test handling of missing columns in feature engineering."""
        # Create data with missing columns
        incomplete_data = pd.DataFrame({
            "Temperature[C]": [25.0, 30.0],
            "Humidity[%]": [50.0, 45.0]
            # Missing other columns
        })
        
        # Should handle missing columns gracefully
        enhanced_data = self.feature_engineer.create_advanced_features(incomplete_data)
        
        # Should still create features for available columns
        assert "temp_squared" in enhanced_data.columns
        assert "humidity_squared" in enhanced_data.columns
        assert "temp_humidity_interaction" in enhanced_data.columns
    
    def test_error_handling_in_feature_creation(self):
        """Test error handling during feature creation."""
        # Create data with problematic values
        problematic_data = pd.DataFrame({
            "Temperature[C]": [25.0, np.inf, np.nan],
            "Humidity[%]": [50.0, -np.inf, 45.0]
        })
        
        # Should handle errors gracefully and return original data
        enhanced_data = self.feature_engineer.create_advanced_features(problematic_data)
        
        # Should at least return the original data
        assert enhanced_data.shape[0] == problematic_data.shape[0]


class TestModelConfig:
    """Test cases for model configuration classes."""
    
    def test_model_config_creation(self):
        """Test model configuration creation."""
        config = ModelConfig(
            name="test_model",
            model_class=RandomForestClassifier,
            param_grid={"n_estimators": [100, 200]},
            requires_scaling=False
        )
        
        assert config.name == "test_model"
        assert config.model_class == RandomForestClassifier
        assert config.param_grid == {"n_estimators": [100, 200]}
        assert config.requires_scaling is False
        assert config.cv_folds == 5  # Default value
    
    def test_training_config_creation(self):
        """Test training configuration creation."""
        config = TrainingConfig(
            random_state=123,
            test_size=0.3,
            use_feature_engineering=False
        )
        
        assert config.random_state == 123
        assert config.test_size == 0.3
        assert config.use_feature_engineering is False
    
    def test_feature_engineering_config_creation(self):
        """Test feature engineering configuration creation."""
        config = FeatureEngineeringConfig(
            create_polynomial_features=False,
            polynomial_degree=3
        )
        
        assert config.create_polynomial_features is False
        assert config.polynomial_degree == 3
        assert config.create_interaction_features is True  # Default value
    
    def test_default_model_configs(self):
        """Test default model configurations."""
        assert "random_forest" in DEFAULT_MODEL_CONFIGS
        assert "logistic_regression" in DEFAULT_MODEL_CONFIGS
        
        rf_config = DEFAULT_MODEL_CONFIGS["random_forest"]
        assert rf_config.model_class == RandomForestClassifier
        assert rf_config.requires_scaling is False
        
        lr_config = DEFAULT_MODEL_CONFIGS["logistic_regression"]
        assert lr_config.model_class == LogisticRegression
        assert lr_config.requires_scaling is True


class TestSmokeDetectionTrainer:
    """Test cases for the main trainer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TrainingConfig(random_state=42, test_size=0.2)
        self.trainer = SmokeDetectionTrainer(self.config)
        
        # Create sample training data
        np.random.seed(42)
        n_samples = 100
        
        self.sample_X = pd.DataFrame({
            "Temperature[C]": np.random.normal(25, 10, n_samples),
            "Humidity[%]": np.random.normal(50, 15, n_samples),
            "TVOC[ppb]": np.random.normal(200, 100, n_samples),
            "eCO2[ppm]": np.random.normal(500, 150, n_samples),
            "Raw H2": np.random.normal(15000, 5000, n_samples),
            "Raw Ethanol": np.random.normal(20000, 7000, n_samples),
            "Pressure[hPa]": np.random.normal(1013, 10, n_samples),
            "PM1.0": np.random.normal(8, 3, n_samples),
            "PM2.5": np.random.normal(12, 5, n_samples),
            "NC0.5": np.random.normal(1500, 500, n_samples),
            "NC1.0": np.random.normal(1000, 300, n_samples),
            "NC2.5": np.random.normal(200, 100, n_samples),
            "CNT": np.random.randint(0, 100, n_samples)
        })
        
        # Create target variable (binary classification)
        self.sample_y = np.random.randint(0, 2, n_samples)
    
    def test_trainer_initialization(self):
        """Test trainer initialization."""
        assert self.trainer.config.random_state == 42
        assert len(self.trainer.models) == 0
        assert len(self.trainer.scalers) == 0
        assert self.trainer.best_model is None
        assert isinstance(self.trainer.feature_engineer, FeatureEngineer)
    
    def test_create_advanced_features_integration(self):
        """Test feature engineering integration in trainer."""
        enhanced_X = self.trainer.create_advanced_features(self.sample_X)
        
        # Should have more features than original
        assert enhanced_X.shape[1] > self.sample_X.shape[1]
        
        # Should update feature columns list
        assert len(self.trainer.feature_columns) == enhanced_X.shape[1]
    
    @patch('ml.training.train_model.bl.load_csv_data')
    def test_load_and_prepare_data_success(self, mock_load_csv):
        """Test successful data loading and preparation."""
        # Create mock data with target column
        mock_data = self.sample_X.copy()
        mock_data["Fire Alarm"] = self.sample_y
        mock_load_csv.return_value = mock_data
        
        X, y = self.trainer.load_and_prepare_data("dummy_path.csv")
        
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, (pd.Series, np.ndarray))
        assert X.shape[0] == len(y)
        assert "Fire Alarm" not in X.columns
    
    @patch('ml.training.train_model.bl.load_csv_data')
    def test_load_and_prepare_data_missing_target(self, mock_load_csv):
        """Test data loading with missing target column."""
        # Mock data without target column
        mock_load_csv.return_value = self.sample_X
        
        with pytest.raises(ValueError, match="Target column.*not found"):
            self.trainer.load_and_prepare_data("dummy_path.csv")
    
    @patch('ml.training.train_model.bl.load_csv_data')
    def test_load_and_prepare_data_empty_dataset(self, mock_load_csv):
        """Test data loading with empty dataset."""
        mock_load_csv.return_value = pd.DataFrame()
        
        with pytest.raises(ValueError, match="Dataset is empty"):
            self.trainer.load_and_prepare_data("dummy_path.csv")
    
    def test_train_models_basic(self):
        """Test basic model training functionality."""
        from sklearn.model_selection import train_test_split
        
        # Split data for testing
        X_train, X_test, y_train, y_test = train_test_split(
            self.sample_X, self.sample_y, test_size=0.2, random_state=42
        )
        
        # Train models (use small param grids for speed)
        small_configs = {
            "random_forest": ModelConfig(
                name="random_forest",
                model_class=RandomForestClassifier,
                param_grid={"n_estimators": [10, 20]},
                requires_scaling=False
            )
        }
        
        with patch.object(self.trainer, '_get_model_configs', return_value=small_configs):
            results = self.trainer.train_models(X_train, X_test, y_train, y_test)
        
        assert "random_forest" in results
        assert "best_model" in results
        assert "comparison" in results
        
        # Check that model was trained
        assert "random_forest" in self.trainer.models
        assert self.trainer.best_model is not None
    
    def test_model_evaluation_metrics(self):
        """Test model evaluation metrics calculation."""
        # Create a simple trained model for testing
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        X_train, X_test, y_train, y_test = train_test_split(
            self.sample_X, self.sample_y, test_size=0.2, random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Test evaluation
        metrics = self.trainer._evaluate_model(model, X_test, y_test)
        
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "auc" in metrics
        
        # All metrics should be between 0 and 1
        for metric_name, value in metrics.items():
            assert 0 <= value <= 1, f"{metric_name} should be between 0 and 1"
    
    def test_save_model_functionality(self):
        """Test model saving functionality."""
        # Create a simple model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(self.sample_X, self.sample_y)
        
        self.trainer.best_model = model
        self.trainer.feature_columns = list(self.sample_X.columns)
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
            model_path = self.trainer.save_model(tmp_file.name)
            
            # Check that file was created
            assert Path(model_path).exists()
            
            # Check that model can be loaded
            with open(model_path, 'rb') as f:
                saved_data = pickle.load(f)
            
            assert "model" in saved_data
            assert "feature_columns" in saved_data
            assert "metadata" in saved_data
            
            # Clean up
            Path(model_path).unlink()
    
    def test_error_handling_in_training(self):
        """Test error handling during model training."""
        # Create problematic data (all same target value)
        problematic_y = np.zeros(len(self.sample_y))  # All zeros
        
        X_train, X_test, y_train, y_test = train_test_split(
            self.sample_X, problematic_y, test_size=0.2, random_state=42
        )
        
        # Should handle training errors gracefully
        small_configs = {
            "random_forest": ModelConfig(
                name="random_forest",
                model_class=RandomForestClassifier,
                param_grid={"n_estimators": [10]},
                requires_scaling=False
            )
        }
        
        with patch.object(self.trainer, '_get_model_configs', return_value=small_configs):
            # Should not raise exception, but may have warnings
            results = self.trainer.train_models(X_train, X_test, y_train, y_test)
            
            # Should still return results structure
            assert isinstance(results, dict)


class TestTrainingPipeline:
    """Test cases for the complete training pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary CSV file with sample data
        np.random.seed(42)
        n_samples = 50  # Small dataset for fast testing
        
        self.sample_data = pd.DataFrame({
            "Temperature[C]": np.random.normal(25, 10, n_samples),
            "Humidity[%]": np.random.normal(50, 15, n_samples),
            "TVOC[ppb]": np.random.normal(200, 100, n_samples),
            "eCO2[ppm]": np.random.normal(500, 150, n_samples),
            "Raw H2": np.random.normal(15000, 5000, n_samples),
            "Raw Ethanol": np.random.normal(20000, 7000, n_samples),
            "Pressure[hPa]": np.random.normal(1013, 10, n_samples),
            "PM1.0": np.random.normal(8, 3, n_samples),
            "PM2.5": np.random.normal(12, 5, n_samples),
            "NC0.5": np.random.normal(1500, 500, n_samples),
            "NC1.0": np.random.normal(1000, 300, n_samples),
            "NC2.5": np.random.normal(200, 100, n_samples),
            "CNT": np.random.randint(0, 100, n_samples),
            "Fire Alarm": np.random.randint(0, 2, n_samples)
        })
        
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        self.sample_data.to_csv(self.temp_file.name, index=False)
        self.temp_file.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.temp_file.name).unlink()
    
    @patch('ml.training.train_model.DEFAULT_MODEL_CONFIGS')
    def test_complete_training_pipeline(self, mock_configs):
        """Test the complete training pipeline."""
        # Use simplified configs for faster testing
        mock_configs.return_value = {
            "random_forest": ModelConfig(
                name="random_forest",
                model_class=RandomForestClassifier,
                param_grid={"n_estimators": [5, 10]},
                requires_scaling=False
            )
        }
        
        config = TrainingConfig(
            random_state=42,
            test_size=0.3,
            use_feature_engineering=True
        )
        
        trainer, results = train_smoke_detection_model(
            data_path=self.temp_file.name,
            config=config
        )
        
        # Check trainer
        assert isinstance(trainer, SmokeDetectionTrainer)
        assert trainer.best_model is not None
        
        # Check results
        assert isinstance(results, dict)
        assert "random_forest" in results
        assert "best_model" in results
    
    def test_training_with_feature_engineering(self):
        """Test training pipeline with feature engineering enabled."""
        config = TrainingConfig(
            random_state=42,
            use_feature_engineering=True
        )
        
        # Mock the model configs to use simple models
        simple_configs = {
            "random_forest": ModelConfig(
                name="random_forest",
                model_class=RandomForestClassifier,
                param_grid={"n_estimators": [5]},
                requires_scaling=False
            )
        }
        
        with patch('ml.training.train_model.DEFAULT_MODEL_CONFIGS', simple_configs):
            trainer, results = train_smoke_detection_model(
                data_path=self.temp_file.name,
                config=config
            )
        
        # Should have created additional features
        assert len(trainer.feature_columns) > len(self.sample_data.columns) - 1  # -1 for target
    
    def test_training_without_feature_engineering(self):
        """Test training pipeline without feature engineering."""
        config = TrainingConfig(
            random_state=42,
            use_feature_engineering=False
        )
        
        simple_configs = {
            "random_forest": ModelConfig(
                name="random_forest",
                model_class=RandomForestClassifier,
                param_grid={"n_estimators": [5]},
                requires_scaling=False
            )
        }
        
        with patch('ml.training.train_model.DEFAULT_MODEL_CONFIGS', simple_configs):
            trainer, results = train_smoke_detection_model(
                data_path=self.temp_file.name,
                config=config
            )
        
        # Should have original number of features (minus target)
        expected_features = len(self.sample_data.columns) - 1
        assert len(trainer.feature_columns) == expected_features


if __name__ == "__main__":
    pytest.main([__file__])
