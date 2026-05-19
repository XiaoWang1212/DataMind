from typing import Any, Dict, List
from sklearn.naive_bayes import MultinomialNB
from .base import BaseModelWrapper

class MultinomialNBModel(BaseModelWrapper):
    name = "Multinomial NB"
    description = "Multinomial naive Bayes classifier for discrete features."

    def create_estimator(self) -> Any:
        return MultinomialNB()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {"alpha": [0.1, 0.5, 1.0], "fit_prior": [True, False]}
        )


