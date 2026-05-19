from typing import Any, Dict, List
from sklearn.neural_network import MLPClassifier
from .base import BaseModelWrapper

class MLPModel(BaseModelWrapper):
    name = "MLP"
    description = "Multi-layer perceptron neural network classifier."

    def create_estimator(self) -> Any:
        return MLPClassifier(random_state=42, max_iter=500)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "hidden_layer_sizes": [(50,), (100,), (50, 50)],
                "activation": ["relu", "tanh"],
                "alpha": [0.0001, 0.001],
            }
        )


