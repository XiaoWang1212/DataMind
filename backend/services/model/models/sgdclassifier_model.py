from typing import Any, Dict, List
from sklearn.linear_model import SGDClassifier
from .base import BaseModelWrapper

class SGDClassifierModel(BaseModelWrapper):
    name = "SGD Classifier"
    description = "Linear classifier optimized with stochastic gradient descent."

    def create_estimator(self) -> Any:
        return SGDClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "loss": ["hinge", "log", "modified_huber"],
                "penalty": ["l2", "l1", "elasticnet"],
                "alpha": [0.0001, 0.001, 0.01],
            }
        )


