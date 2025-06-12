"""
Comprehensive ML model training for IoT smoke detection.

This module provides a complete machine learning training pipeline for IoT smoke detection
with the following capabilities:

- Multi-algorithm support (RandomForest, LogisticRegression)
- Automated hyperparameter tuning with GridSearchCV
- Advanced feature engineering with domain-specific features
- Comprehensive model evaluation and visualization
- Model persistence with metadata
- Scalable training pipeline design

Classes:
    SmokeDetectionTrainer: Main trainer class for smoke detection models
    ModelConfig: Configuration class for model parameters
    FeatureEngineer: Specialized class for feature engineering
    ModelEvaluator: Comprehensive model evaluation utilities

Functions:
    train_smoke_detection_model: Main training pipeline function
    create_model_configs: Factory function for model configurations
    setup_logging: Configure logging for training process

Constants:
    DEFAULT_MODEL_PARAMS: Default hyperparameter grids
    FEATURE_ENGINEERING_CONFIG: Configuration for feature creation
    EVALUATION_METRICS: List of evaluation metrics to compute
"""

import sys
from pathlib import Path

# Get the current absolute path and add project root to sys.path
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
sys.path.append(str(project_root))

import pandas as pd
import numpy as np
import pickle
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List, Union
from dataclasses import dataclass, field

# ML libraries
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    roc_curve,
)
import matplotlib.pyplot as plt
import seaborn as sns

# Project imports
from config.constants import CLEANED_DATA_FILE, TARGET_COLUMN
from config.env_config import MODEL_PATH
from app.utils.path_utils import DATA_DIR, build_relative_path
from data_ingestion.batch import batch_loader as bl

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for ML model training."""

    name: str
    model_class: type
    param_grid: Dict[str, List[Any]]
    requires_scaling: bool = True
    cv_folds: int = 5
    scoring_metric: str = "f1"
    n_jobs: int = -1


@dataclass
class TrainingConfig:
    """Configuration for training pipeline."""

    random_state: int = 42
    test_size: float = 0.2
    use_feature_engineering: bool = True
    save_plots: bool = True
    plots_dir: str = "ml/plots"
    models_dir: str = "ml/models"
    include_scaler: bool = True


@dataclass
class FeatureEngineeringConfig:
    """Configuration for feature engineering."""

    create_polynomial_features: bool = True
    create_interaction_features: bool = True
    create_ratio_features: bool = True
    create_log_features: bool = True
    polynomial_degree: int = 2
    interaction_only: bool = True


# Default model configurations
DEFAULT_MODEL_CONFIGS = {
    "random_forest": ModelConfig(
        name="random_forest",
        model_class=RandomForestClassifier,
        param_grid={
            "n_estimators": [100, 200, 300],
            "max_depth": [10, 20, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2"],
        },
        requires_scaling=False,
    ),
    "logistic_regression": ModelConfig(
        name="logistic_regression",
        model_class=LogisticRegression,
        param_grid={
            "C": [0.1, 1.0, 10.0, 100.0],
            "penalty": ["l1", "l2"],
            "solver": ["liblinear", "saga"],
        },
        requires_scaling=True,
    ),
}

# Evaluation metrics to compute
EVALUATION_METRICS = ["accuracy", "precision", "recall", "f1", "auc"]


class FeatureEngineer:
    """Specialized class for feature engineering operations."""

    def __init__(self, config: FeatureEngineeringConfig = FeatureEngineeringConfig()):
        self.config = config
        self.created_features = []

    def create_advanced_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Create advanced engineered features for smoke detection.

        This method creates domain-specific features including:
        - Temperature and humidity interactions
        - Air quality ratios and combinations
        - Particulate matter features
        - Gas sensor combinations
        - Logarithmic transformations

        Args:
            X: Input feature DataFrame

        Returns:
            Enhanced DataFrame with additional features
        """
        logger.info("Creating advanced features...")
        X_enhanced = X.copy()
        initial_features = X.shape[1]

        try:
            # Temperature-based features
            if "Temperature[C]" in X.columns:
                X_enhanced["temp_squared"] = X["Temperature[C]"] ** 2
                X_enhanced["temp_log"] = np.log1p(
                    X["Temperature[C]"] + 50
                )  # Handle negative temps
                self.created_features.extend(["temp_squared", "temp_log"])

            # Humidity-based features
            if "Humidity[%]" in X.columns:
                X_enhanced["humidity_squared"] = X["Humidity[%]"] ** 2
                X_enhanced["humidity_log"] = np.log1p(X["Humidity[%]"])
                self.created_features.extend(["humidity_squared", "humidity_log"])

            # Air quality ratios
            if "TVOC[ppb]" in X.columns and "eCO2[ppm]" in X.columns:
                X_enhanced["tvoc_eco2_ratio"] = X["TVOC[ppb]"] / (X["eCO2[ppm]"] + 1e-5)
                self.created_features.append("tvoc_eco2_ratio")

            # Particulate matter features
            if "PM1.0" in X.columns and "PM2.5" in X.columns:
                X_enhanced["pm_ratio"] = X["PM1.0"] / (X["PM2.5"] + 1e-5)
                X_enhanced["pm_sum"] = X["PM1.0"] + X["PM2.5"]
                self.created_features.extend(["pm_ratio", "pm_sum"])

            # Pressure features
            if "Pressure[hPa]" in X.columns:
                X_enhanced["pressure_deviation"] = abs(X["Pressure[hPa]"] - 1013.25)
                self.created_features.append("pressure_deviation")

            # Interaction features
            if "Temperature[C]" in X.columns and "Humidity[%]" in X.columns:
                X_enhanced["temp_humidity_interaction"] = (
                    X["Temperature[C]"] * X["Humidity[%]"]
                )
                X_enhanced["heat_index"] = X["Temperature[C]"] + 0.5 * X["Humidity[%]"]
                self.created_features.extend(
                    ["temp_humidity_interaction", "heat_index"]
                )

            # Gas sensor combinations
            if "Raw H2" in X.columns and "Raw Ethanol" in X.columns:
                X_enhanced["gas_sensor_ratio"] = X["Raw H2"] / (X["Raw Ethanol"] + 1e-5)
                X_enhanced["gas_sensor_sum"] = X["Raw H2"] + X["Raw Ethanol"]
                self.created_features.extend(["gas_sensor_ratio", "gas_sensor_sum"])

            logger.info(
                f"Enhanced features: {X_enhanced.shape[1]} columns "
                f"(added {X_enhanced.shape[1] - initial_features} features)"
            )

            return X_enhanced

        except Exception as e:
            logger.error(f"Error creating advanced features: {e}")
            return X


class SmokeDetectionTrainer:
    """
    Comprehensive trainer for smoke detection ML models.

    This class provides a complete training pipeline including:
    - Data loading and preprocessing
    - Feature engineering
    - Model training with hyperparameter tuning
    - Model evaluation and visualization
    - Model persistence
    """

    def __init__(self, config: TrainingConfig = TrainingConfig()):
        self.config = config
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.target_column = TARGET_COLUMN
        self.best_model = None
        self.best_model_name = None
        self.training_history = {}
        self.feature_engineer = FeatureEngineer()

        # For backward compatibility
        self.random_state = config.random_state

    def load_and_prepare_data(
        self, data_path: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load and prepare data for training with comprehensive validation.

        Args:
            data_path: Path to the training data CSV file

        Returns:
            Tuple of (features_dataframe, target_series)

        Raises:
            ValueError: If data is empty or target column is missing
            FileNotFoundError: If data file doesn't exist
        """
        if data_path is None:
            data_path = str(build_relative_path(DATA_DIR, CLEANED_DATA_FILE))

        logger.info(f"Loading data from {data_path}")

        try:
            # Load data
            df = bl.load_csv_data(data_path)
            logger.info(f"Loaded dataset with shape: {df.shape}")

            # Basic data validation
            if df.empty:
                raise ValueError("Dataset is empty")

            if self.target_column not in df.columns:
                raise ValueError(
                    f"Target column '{self.target_column}' not found in dataset"
                )

            # Prepare features and target
            feature_columns = [col for col in df.columns if col != self.target_column]
            self.feature_columns = feature_columns

            X = df[feature_columns]
            y = df[self.target_column]

            # Convert target to numeric if needed
            if y.dtype == "object" or y.dtype.name == "category":
                le = LabelEncoder()
                y = le.fit_transform(y)
                logger.info(f"Converted target to numeric. Classes: {le.classes_}")

            # Handle missing values
            X = X.fillna(X.median())

            logger.info(f"Features: {len(feature_columns)} columns")
            logger.info(f"Target distribution: {pd.Series(y).value_counts().to_dict()}")

            return X, y

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def create_advanced_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Create advanced engineered features using the FeatureEngineer.

        Args:
            X: Input feature DataFrame

        Returns:
            Enhanced DataFrame with additional features
        """
        X_enhanced = self.feature_engineer.create_advanced_features(X)
        # Update feature columns list
        self.feature_columns = X_enhanced.columns.tolist()
        return X_enhanced

    def setup_models(self) -> Dict[str, Any]:
        """Setup ML models with hyperparameter grids"""

        models = {
            "random_forest": {
                "model": RandomForestClassifier(random_state=self.random_state),
                "params": {
                    "n_estimators": [100, 200, 300],
                    "max_depth": [10, 20, None],
                    "min_samples_split": [2, 5, 10],
                    "min_samples_leaf": [1, 2, 4],
                    "max_features": ["sqrt", "log2"],
                },
            },
            "logistic_regression": {
                "model": LogisticRegression(
                    random_state=self.random_state, max_iter=1000
                ),
                "params": {
                    "C": [0.1, 1.0, 10.0, 100.0],
                    "penalty": ["l1", "l2"],
                    "solver": ["liblinear", "saga"],
                },
            },
        }

        return models

    def train_models(
        self, X_train, X_test, y_train, y_test, use_scaling: bool = True
    ) -> Dict[str, Any]:
        """Train multiple models with hyperparameter tuning"""

        logger.info("Starting model training...")

        # Setup models
        models_config = self.setup_models()
        results = {}

        # Scale features if needed
        if use_scaling:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            self.scalers["standard"] = scaler
        else:
            X_train_scaled = X_train
            X_test_scaled = X_test

        for model_name, config in models_config.items():
            logger.info(f"Training {model_name}...")

            try:
                # Grid search with cross-validation
                grid_search = GridSearchCV(
                    config["model"],
                    config["params"],
                    cv=5,
                    scoring="f1",
                    n_jobs=-1,
                    verbose=1,
                )

                # Fit the model
                grid_search.fit(X_train_scaled, y_train)

                # Get best model
                best_model = grid_search.best_estimator_

                # Make predictions
                y_pred = best_model.predict(X_test_scaled)
                y_pred_proba = (
                    best_model.predict_proba(X_test_scaled)[:, 1]
                    if hasattr(best_model, "predict_proba")
                    else None
                )

                # Calculate metrics
                metrics = self._calculate_metrics(y_test, y_pred, y_pred_proba)

                # Store results
                results[model_name] = {
                    "model": best_model,
                    "best_params": grid_search.best_params_,
                    "best_score": grid_search.best_score_,
                    "metrics": metrics,
                    "predictions": y_pred,
                    "probabilities": y_pred_proba,
                }

                # Store in class
                self.models[model_name] = best_model

                logger.info(
                    f"{model_name} - Best CV Score: {grid_search.best_score_:.4f}"
                )
                logger.info(f"{model_name} - Test F1 Score: {metrics['f1']:.4f}")

            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
                continue

        # Select best model
        if results:
            best_model_name = max(
                results.keys(), key=lambda k: results[k]["metrics"]["f1"]
            )
            self.best_model = results[best_model_name]["model"]
            self.best_model_name = best_model_name

            logger.info(
                f"Best model: {best_model_name} with F1 score: {results[best_model_name]['metrics']['f1']:.4f}"
            )

        return results

    def _calculate_metrics(self, y_true, y_pred, y_pred_proba=None) -> Dict[str, float]:
        """Calculate comprehensive evaluation metrics"""

        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, average="weighted"),
            "recall": recall_score(y_true, y_pred, average="weighted"),
            "f1": f1_score(y_true, y_pred, average="weighted"),
        }

        # Add AUC if probabilities available
        if y_pred_proba is not None:
            try:
                metrics["auc"] = roc_auc_score(y_true, y_pred_proba)
            except ValueError:
                metrics["auc"] = None

        return metrics

    def save_model(self, model_path: Optional[str] = None, include_scaler: bool = True):
        """Save the best trained model"""

        if self.best_model is None:
            raise ValueError("No trained model to save. Train a model first.")

        if model_path is None:
            model_path = f"ml/models/smoke_detection_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        # Create directory if it doesn't exist
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)

        # Prepare model package
        model_package = {
            "model": self.best_model,
            "model_name": self.best_model_name,
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "training_timestamp": datetime.now().isoformat(),
            "scaler": self.scalers.get("standard") if include_scaler else None,
        }

        # Save model
        with open(model_path, "wb") as f:
            pickle.dump(model_package, f)

        logger.info(f"Model saved to {model_path}")
        return model_path

    def create_visualizations(
        self, results: Dict[str, Any], y_test, save_plots: bool = True
    ):
        """Create and save visualization plots"""

        if not results:
            logger.warning("No results to visualize")
            return

        # Create plots directory
        plots_dir = Path("ml/plots")
        plots_dir.mkdir(parents=True, exist_ok=True)

        # 1. Model comparison plot
        self._plot_model_comparison(results, plots_dir if save_plots else None)

        # 2. Confusion matrices
        self._plot_confusion_matrices(
            results, y_test, plots_dir if save_plots else None
        )

        # 3. ROC curves
        self._plot_roc_curves(results, y_test, plots_dir if save_plots else None)

        # 4. Feature importance (for tree-based models)
        self._plot_feature_importance(results, plots_dir if save_plots else None)

        logger.info("Visualizations created successfully")

    def _plot_model_comparison(
        self, results: Dict[str, Any], save_dir: Optional[Path] = None
    ):
        """Plot model performance comparison"""

        models = list(results.keys())
        metrics = ["accuracy", "precision", "recall", "f1"]

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.ravel()

        for i, metric in enumerate(metrics):
            values = [results[model]["metrics"][metric] for model in models]
            axes[i].bar(models, values)
            axes[i].set_title(f"{metric.capitalize()} Comparison")
            axes[i].set_ylabel(metric.capitalize())
            axes[i].tick_params(axis="x", rotation=45)

            # Add value labels on bars
            for j, v in enumerate(values):
                axes[i].text(j, v + 0.01, f"{v:.3f}", ha="center")

        plt.tight_layout()

        if save_dir:
            plt.savefig(save_dir / "model_comparison.png", dpi=300, bbox_inches="tight")
            logger.info(
                f"Model comparison plot saved to {save_dir / 'model_comparison.png'}"
            )

        plt.show()

    def _plot_confusion_matrices(
        self, results: Dict[str, Any], y_test, save_dir: Optional[Path] = None
    ):
        """Plot confusion matrices for all models"""

        n_models = len(results)
        fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4))

        if n_models == 1:
            axes = [axes]

        for i, (model_name, result) in enumerate(results.items()):
            cm = confusion_matrix(y_test, result["predictions"])

            sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[i])
            axes[i].set_title(
                f'{model_name.replace("_", " ").title()}\nConfusion Matrix'
            )
            axes[i].set_xlabel("Predicted")
            axes[i].set_ylabel("Actual")

        plt.tight_layout()

        if save_dir:
            plt.savefig(
                save_dir / "confusion_matrices.png", dpi=300, bbox_inches="tight"
            )
            logger.info(
                f"Confusion matrices saved to {save_dir / 'confusion_matrices.png'}"
            )

        plt.show()

    def _plot_roc_curves(
        self, results: Dict[str, Any], y_test, save_dir: Optional[Path] = None
    ):
        """Plot ROC curves for models with probability predictions"""

        plt.figure(figsize=(8, 6))

        for model_name, result in results.items():
            if result["probabilities"] is not None:
                fpr, tpr, _ = roc_curve(y_test, result["probabilities"])
                auc_score = result["metrics"].get("auc", 0)
                plt.plot(
                    fpr,
                    tpr,
                    label=f'{model_name.replace("_", " ").title()} (AUC = {auc_score:.3f})',
                )

        plt.plot([0, 1], [0, 1], "k--", label="Random")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curves Comparison")
        plt.legend()
        plt.grid(True, alpha=0.3)

        if save_dir:
            plt.savefig(save_dir / "roc_curves.png", dpi=300, bbox_inches="tight")
            logger.info(f"ROC curves saved to {save_dir / 'roc_curves.png'}")

        plt.show()

    def _plot_feature_importance(
        self, results: Dict[str, Any], save_dir: Optional[Path] = None
    ):
        """Plot feature importance for tree-based models"""

        for model_name, result in results.items():
            model = result["model"]

            if hasattr(model, "feature_importances_"):
                # Get feature importance
                importance = model.feature_importances_
                feature_names = self.feature_columns

                # Sort by importance
                indices = np.argsort(importance)[::-1]

                # Plot top 20 features
                top_n = min(20, len(feature_names))

                plt.figure(figsize=(10, 8))
                plt.title(
                    f'Feature Importance - {model_name.replace("_", " ").title()}'
                )
                plt.bar(range(top_n), importance[indices[:top_n]])
                plt.xticks(
                    range(top_n),
                    [feature_names[i] for i in indices[:top_n]],
                    rotation=45,
                    ha="right",
                )
                plt.xlabel("Features")
                plt.ylabel("Importance")
                plt.tight_layout()

                if save_dir:
                    plt.savefig(
                        save_dir / f"feature_importance_{model_name}.png",
                        dpi=300,
                        bbox_inches="tight",
                    )
                    logger.info(
                        f"Feature importance plot saved to {save_dir / f'feature_importance_{model_name}.png'}"
                    )

                plt.show()


def train_smoke_detection_model(
    data_path: Optional[str] = None,
    test_size: float = 0.2,
    random_state: int = 42,
    config: Optional[TrainingConfig] = None,
) -> Tuple[SmokeDetectionTrainer, Dict[str, Any]]:
    """
    Main function to train smoke detection model with comprehensive pipeline.

    Args:
        data_path: Path to training data CSV file
        test_size: Fraction of data to use for testing
        random_state: Random seed for reproducibility
        config: Training configuration object

    Returns:
        Tuple of (trained_model, training_results)

    Raises:
        ValueError: If no models are successfully trained
        FileNotFoundError: If data file doesn't exist
    """
    logger.info("Starting smoke detection model training pipeline...")

    # Initialize configuration
    if config is None:
        config = TrainingConfig(random_state=random_state, test_size=test_size)

    # Initialize trainer
    trainer = SmokeDetectionTrainer(config)

    try:
        # Load and prepare data
        X, y = trainer.load_and_prepare_data(data_path)

        # Create advanced features
        X_enhanced = trainer.create_advanced_features(X)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_enhanced, y, test_size=test_size, random_state=random_state, stratify=y
        )

        logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

        # Train models
        results = trainer.train_models(X_train, X_test, y_train, y_test)

        if not results:
            raise ValueError("No models were successfully trained")

        # Create visualizations
        trainer.create_visualizations(results, y_test)

        # Save best model
        # Save with timestamp for versioning
        timestamped_model_path = trainer.save_model()

        # Also save to the expected location for Flask API
        expected_model_path = MODEL_PATH
        trainer.save_model(model_path=expected_model_path)

        logger.info(f"Model saved to expected path: {expected_model_path}")
        model_path = expected_model_path

        # Print final results
        logger.info("\n" + "=" * 50)
        logger.info("TRAINING COMPLETED SUCCESSFULLY")
        logger.info("=" * 50)

        for model_name, result in results.items():
            logger.info(f"\n{model_name.upper()} RESULTS:")
            logger.info(f"  Best Parameters: {result['best_params']}")
            logger.info(f"  CV Score: {result['best_score']:.4f}")
            for metric, value in result["metrics"].items():
                if value is not None:
                    logger.info(f"  {metric.capitalize()}: {value:.4f}")

        logger.info(f"\nBest Model: {trainer.best_model_name}")
        logger.info(f"Model saved to: {model_path}")

        return trainer, results

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    # Run training
    trainer, results = train_smoke_detection_model()

    logger.info("Training pipeline completed successfully!")
