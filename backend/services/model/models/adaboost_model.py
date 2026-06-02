from typing import Any, Dict, List
from sklearn.ensemble import AdaBoostClassifier
from .base import BaseModelWrapper

class AdaBoostModel(BaseModelWrapper):
    name = "AdaBoost"
    description = "Adaptive boosting classifier."

    def create_estimator(self) -> Any:
        return AdaBoostClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 150, 250],
                "learning_rate": [0.01, 0.1, 0.5],
            }
        )
