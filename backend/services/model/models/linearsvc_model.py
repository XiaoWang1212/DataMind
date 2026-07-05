from typing import Any, Dict, List

from sklearn.calibration import CalibratedClassifierCV
from sklearn.svm import LinearSVC

from .base import BaseModelWrapper


class LinearSVCModel(BaseModelWrapper):
    name = "Linear SVC"
    description = "Fast linear SVM for high-dimensional data, wrapped with probability calibration."

    def create_estimator(self) -> Any:
        return CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", max_iter=2000, random_state=42),
            cv=3,
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "estimator__C": [0.01, 0.1, 1.0, 10.0],
            "estimator__loss": ["hinge", "squared_hinge"],
            "estimator__class_weight": ["balanced", None],
        }
