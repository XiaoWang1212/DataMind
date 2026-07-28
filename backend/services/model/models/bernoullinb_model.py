from typing import Any, Dict, List
from sklearn.naive_bayes import BernoulliNB
from .base import BaseModelWrapper

class BernoulliNBModel(BaseModelWrapper):
    name = "Bernoulli NB"
    description = "Bernoulli naive Bayes classifier."

    def create_estimator(self) -> Any:
        return BernoulliNB()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid({"alpha": [0.5, 1.0]})


