from typing import Any, Dict, List
from sklearn.ensemble import ExtraTreesClassifier
from .base import BaseModelWrapper

class ExtraTreesModel(BaseModelWrapper):
    name = "Extra Trees"
    description = "Extremely randomized trees ensemble."

    def create_estimator(self) -> Any:
        return ExtraTreesClassifier(random_state=42, n_jobs=-1)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 150, 250],
                "max_depth": [5, 10, 20],
            }
        )


