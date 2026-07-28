from typing import Any, Dict, List
from sklearn.ensemble import GradientBoostingClassifier
from .base import BaseModelWrapper

class GradientBoostingModel(BaseModelWrapper):
    name = "Gradient Boosting"
    description = "Gradient boosting classifier."

    def create_estimator(self) -> Any:
        return GradientBoostingClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 150, 250],
                "learning_rate": [0.01, 0.1],
                "max_depth": [3, 5],
            }
        )


