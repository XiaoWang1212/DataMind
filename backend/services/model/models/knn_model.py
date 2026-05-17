from typing import Any, Dict, List
from sklearn.neighbors import KNeighborsClassifier
from .base import BaseModelWrapper

class KNNModel(BaseModelWrapper):
    name = "K-Nearest Neighbors"
    description = "K-nearest neighbors classifier."

    def create_estimator(self) -> Any:
        return KNeighborsClassifier()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_neighbors": [3, 5, 7],
                "weights": ["uniform", "distance"],
            }
        )


