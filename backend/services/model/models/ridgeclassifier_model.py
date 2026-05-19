from typing import Any, Dict, List
from sklearn.linear_model import RidgeClassifier
from .base import BaseModelWrapper

class RidgeClassifierModel(BaseModelWrapper):
    name = "Ridge Classifier"
    description = "Linear classifier with ridge regularization."

    def create_estimator(self) -> Any:
        return RidgeClassifier()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid({"alpha": [0.1, 1.0, 10.0]})


