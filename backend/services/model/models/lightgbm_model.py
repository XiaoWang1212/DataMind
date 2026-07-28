from typing import Any, Dict, List
from .base import BaseModelWrapper
from lightgbm import LGBMClassifier

class LightGBMModel(BaseModelWrapper):
    name = "LightGBM"
    description = "LightGBM gradient boosting classifier."

    def create_estimator(self) -> Any:
        return LGBMClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 150, 250],
                "learning_rate": [0.01, 0.1],
                "max_depth": [3, 6, 10],
            }
        )


