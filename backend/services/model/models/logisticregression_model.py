from typing import Any, Dict, List
from sklearn.linear_model import LogisticRegression
from .base import BaseModelWrapper

class LogisticRegressionModel(BaseModelWrapper):
    name = "Logistic Regression"
    description = "Binary classification with regularized logistic regression."

    def create_estimator(self) -> Any:
        return LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            solver="liblinear",
            random_state=42,
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "penalty": ["l1", "l2", "elasticnet", "none"],
                "C": [0.01, 0.1, 1.0, 10.0, 100.0],
                "solver": ["liblinear", "saga", "lbfgs", "newton-cg", "sag"],
                "class_weight": ["balanced", None],
                "max_iter": [200, 500, 1000, 2000],
                "fit_intercept": [True, False],
                "tol": [1e-4, 1e-3, 1e-2],
                "dual": [False],
                "l1_ratio": [0.0, 0.15, 0.5],
            }
        )


