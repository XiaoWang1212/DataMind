from typing import Any, Dict, List
from sklearn.naive_bayes import ComplementNB
from .base import BaseModelWrapper

class ComplementNBModel(BaseModelWrapper):
    name = "Complement NB"
    description = "Complement naive Bayes classifier for imbalanced data."

    def create_estimator(self) -> Any:
        return ComplementNB()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {"alpha": [0.1, 0.5, 1.0], "norm": [True, False]}
        )


