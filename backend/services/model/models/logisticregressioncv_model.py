from typing import Any, Dict, List

from sklearn.linear_model import LogisticRegressionCV

from .base import BaseModelWrapper


class LogisticRegressionCVModel(BaseModelWrapper):
    name = "Logistic Regression CV"
    description = "Logistic regression with built-in cross-validated regularization selection."

    def create_estimator(self) -> Any:
        return LogisticRegressionCV(
            Cs=10,
            cv=5,
            penalty="l2",
            solver="lbfgs",
            class_weight="balanced",
            max_iter=2000,
            random_state=42,
            n_jobs=-1,
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "Cs": [5, 10, 20],
            "class_weight": ["balanced", None],
            "max_iter": [1000, 2000],
        }
