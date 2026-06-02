from typing import Any, Dict, List
from .base import BaseModelWrapper
from imblearn.ensemble import BalancedRandomForestClassifier


class BalancedRandomForestModel(BaseModelWrapper):
    name = "Balanced Random Forest"
    description = "Imbalanced-data random forest with class balancing."

    def create_estimator(self) -> Any:
        return BalancedRandomForestClassifier(random_state=42, n_jobs=-1)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 100],
                "max_depth": [None, 10, 20],
            }
        )


