from typing import Any, Dict, List
from sklearn.neighbors import RadiusNeighborsClassifier
from .base import BaseModelWrapper

class RadiusNeighborsModel(BaseModelWrapper):
    name = "Radius Neighbors"
    description = "Radius neighbors classifier for local decision boundaries."

    def create_estimator(self) -> Any:
        return RadiusNeighborsClassifier(radius=1.0)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "radius": [0.5, 1.0, 2.0],
                "weights": ["uniform", "distance"],
            }
        )


