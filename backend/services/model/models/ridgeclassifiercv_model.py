from typing import Any, Dict, List

from sklearn.linear_model import RidgeClassifierCV

from .base import BaseModelWrapper


class RidgeClassifierCVModel(BaseModelWrapper):
    name = "Ridge Classifier CV"
    description = "Ridge classifier with built-in cross-validated alpha selection."

    def create_estimator(self) -> Any:
        return RidgeClassifierCV(
            alphas=(0.1, 1.0, 10.0, 100.0),
            class_weight="balanced",
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "alphas": [
                (0.01, 0.1, 1.0),
                (0.1, 1.0, 10.0),
                (1.0, 10.0, 100.0),
            ],
            "class_weight": ["balanced", None],
            "fit_intercept": [True, False],
        }
