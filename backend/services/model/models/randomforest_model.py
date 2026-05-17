from typing import Any, Dict, List
from sklearn.ensemble import RandomForestClassifier
from .base import BaseModelWrapper

class RandomForestModel(BaseModelWrapper):
    name = "Random Forest"
    description = "Tree-based ensemble with class balancing."

    def create_estimator(self) -> Any:
        return RandomForestClassifier(
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 150, 250],
                "max_depth": [5, 10, 20],
                "min_samples_leaf": [1, 2, 4],
            }
        )


