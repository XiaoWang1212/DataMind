from typing import Any, Dict, List
from sklearn.ensemble import HistGradientBoostingClassifier
from .base import BaseModelWrapper

class HistGradientBoostingModel(BaseModelWrapper):
    name = "HistGradient Boosting"
    description = "Histogram-based gradient boosting classifier."

    def create_estimator(self) -> Any:
        return HistGradientBoostingClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "max_iter": [100, 200],
                "learning_rate": [0.05, 0.1],
                "max_depth": [None, 10, 20],
            }
        )


