from typing import Any, Dict, List
from sklearn.ensemble import BaggingClassifier
from .base import BaseModelWrapper

class BaggingModel(BaseModelWrapper):
    name = "Bagging"
    description = "Bagging ensemble of base estimators."

    def create_estimator(self) -> Any:
        return BaggingClassifier(random_state=42, n_jobs=-1)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [10, 50, 100],
                "max_samples": [0.5, 1.0],
            }
        )


