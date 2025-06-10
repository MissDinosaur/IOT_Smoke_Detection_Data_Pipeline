"""
Comprehensive model evaluation for IoT smoke detection.
Provides detailed analysis of model performance and generates evaluation reports.
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
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

# ML libraries
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
)
import matplotlib.pyplot as plt
import seaborn as sns

# Project imports
from config.constants import CLEANED_DATA_FILE, TARGET_COLUMN
from app.utils.path_utils import DATA_DIR, build_relative_path
from data_ingestion.batch import batch_loader as bl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("ml_evaluation.log"), logging.StreamHandler()],
)
logger = logging.getLogger("ml_evaluation")


class ModelEvaluator:
    """Comprehensive model evaluator for smoke detection models"""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model_package = None
        self.model = None
        self.feature_columns = None
        self.target_column = None
        self.scaler = None
        self.load_model()

    def load_model(self):
        """Load trained model from pickle file"""
        try:
            with open(self.model_path, "rb") as f:
                self.model_package = pickle.load(f)

            self.model = self.model_package["model"]
            self.feature_columns = self.model_package["feature_columns"]
            self.target_column = self.model_package.get("target_column", TARGET_COLUMN)
            self.scaler = self.model_package.get("scaler")

            logger.info(f"Model loaded successfully from {self.model_path}")
            logger.info(f"Model type: {type(self.model).__name__}")
            logger.info(f"Features: {len(self.feature_columns)}")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def evaluate_on_test_data(
        self, test_data_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate model on test dataset"""

        if test_data_path is None:
            test_data_path = build_relative_path(DATA_DIR, CLEANED_DATA_FILE)

        logger.info(f"Evaluating model on test data: {test_data_path}")

        # Load test data
        df = bl.load_csv_data(test_data_path)

        # Prepare features and target
        X = df[self.feature_columns]
        y = df[self.target_column]

        # Convert target to numeric if needed
        if y.dtype == "object" or y.dtype.name == "category":
            from sklearn.preprocessing import LabelEncoder

            le = LabelEncoder()
            y = le.fit_transform(y)

        # Handle missing values
        X = X.fillna(X.median())

        # Scale features if scaler available
        if self.scaler is not None:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X

        # Make predictions
        y_pred = self.model.predict(X_scaled)
        y_pred_proba = None

        if hasattr(self.model, "predict_proba"):
            y_pred_proba = self.model.predict_proba(X_scaled)[:, 1]

        # Calculate comprehensive metrics
        evaluation_results = self._calculate_comprehensive_metrics(
            y, y_pred, y_pred_proba
        )

        # Add prediction details
        evaluation_results["predictions"] = {
            "y_true": y.tolist(),
            "y_pred": y_pred.tolist(),
            "y_pred_proba": y_pred_proba.tolist() if y_pred_proba is not None else None,
        }

        return evaluation_results

    def _calculate_comprehensive_metrics(
        self, y_true, y_pred, y_pred_proba=None
    ) -> Dict[str, Any]:
        """Calculate comprehensive evaluation metrics"""

        metrics = {
            "basic_metrics": {
                "accuracy": accuracy_score(y_true, y_pred),
                "precision": precision_score(y_true, y_pred, average="weighted"),
                "recall": recall_score(y_true, y_pred, average="weighted"),
                "f1_score": f1_score(y_true, y_pred, average="weighted"),
                "precision_macro": precision_score(y_true, y_pred, average="macro"),
                "recall_macro": recall_score(y_true, y_pred, average="macro"),
                "f1_macro": f1_score(y_true, y_pred, average="macro"),
            },
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
            "classification_report": classification_report(
                y_true, y_pred, output_dict=True
            ),
        }

        # Add probability-based metrics if available
        if y_pred_proba is not None:
            try:
                metrics["probability_metrics"] = {
                    "roc_auc": roc_auc_score(y_true, y_pred_proba),
                    "average_precision": average_precision_score(y_true, y_pred_proba),
                }

                # ROC curve data
                fpr, tpr, roc_thresholds = roc_curve(y_true, y_pred_proba)
                metrics["roc_curve"] = {
                    "fpr": fpr.tolist(),
                    "tpr": tpr.tolist(),
                    "thresholds": roc_thresholds.tolist(),
                }

                # Precision-Recall curve data
                precision, recall, pr_thresholds = precision_recall_curve(
                    y_true, y_pred_proba
                )
                metrics["pr_curve"] = {
                    "precision": precision.tolist(),
                    "recall": recall.tolist(),
                    "thresholds": pr_thresholds.tolist(),
                }

            except ValueError as e:
                logger.warning(f"Could not calculate probability metrics: {e}")
                metrics["probability_metrics"] = None

        return metrics

    def create_evaluation_report(
        self, evaluation_results: Dict[str, Any], save_path: Optional[str] = None
    ) -> str:
        """Create comprehensive evaluation report"""

        if save_path is None:
            save_path = f"ml/reports/evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Create directory if it doesn't exist
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # Prepare report
        report = {
            "model_info": {
                "model_path": self.model_path,
                "model_type": type(self.model).__name__,
                "feature_count": len(self.feature_columns),
                "features": self.feature_columns,
                "target_column": self.target_column,
                "has_scaler": self.scaler is not None,
                "evaluation_timestamp": datetime.now().isoformat(),
            },
            "evaluation_results": evaluation_results,
        }

        # Save report
        with open(save_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Evaluation report saved to {save_path}")
        return save_path
