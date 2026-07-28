from typing import Any, Dict, List
from sklearn.tree import DecisionTreeClassifier
from .base import BaseModelWrapper

class DecisionTreeModel(BaseModelWrapper):
    name = "Decision Tree"
    description = "Single decision tree classifier."

    def create_estimator(self) -> Any:
        return DecisionTreeClassifier(random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "max_depth": [3, 5, 10, None],
                "min_samples_leaf": [1, 2, 4],
            }
        )


