from typing import Any, Dict, List
from sklearn.naive_bayes import GaussianNB
from .base import BaseModelWrapper

class GaussianNBModel(BaseModelWrapper):
    name = "Gaussian NB"
    description = "Gaussian Naive Bayes classifier."

    def create_estimator(self) -> Any:
        return GaussianNB()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid({})


