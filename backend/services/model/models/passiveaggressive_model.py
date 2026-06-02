from typing import Any, Dict, List
from sklearn.linear_model import PassiveAggressiveClassifier
from .base import BaseModelWrapper

class PassiveAggressiveModel(BaseModelWrapper):
    name = "Passive Aggressive"
    description = "Passive aggressive classifier for large-scale learning."

    def create_estimator(self) -> Any:
        return PassiveAggressiveClassifier(random_state=42, max_iter=1000)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "C": [0.1, 1.0, 10.0],
                "loss": ["hinge", "squared_hinge"],
            }
        )


