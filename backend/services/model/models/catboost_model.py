from typing import Any, Dict, List
from .base import BaseModelWrapper
from catboost import CatBoostClassifier

class CatBoostModel(BaseModelWrapper):
    name = "CatBoost"
    description = "CatBoost classifier for categorical-aware boosting."

    def create_estimator(self) -> Any:
        return CatBoostClassifier(verbose=0, random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "iterations": [100, 200],
                "learning_rate": [0.01, 0.1],
                "depth": [4, 6, 8],
            }
        )
