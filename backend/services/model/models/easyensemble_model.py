from typing import Any, Dict, List
from .base import BaseModelWrapper
from imblearn.ensemble import EasyEnsembleClassifier

class EasyEnsembleModel(BaseModelWrapper):
    name = "Easy Ensemble"
    description = "Ensemble classifier using easy ensemble resampling."

    def create_estimator(self) -> Any:
        return EasyEnsembleClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [10, 20],
                "base_estimator__max_depth": [3, 5],
            }
        )


