from typing import Any, Dict, List
from sklearn.svm import SVC
from .base import BaseModelWrapper

class SVMModel(BaseModelWrapper):
    name = "SVM"
    description = "Support vector machine classifier."

    def create_estimator(self) -> Any:
        return SVC(probability=True, random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "C": [0.1, 1.0, 10.0],
                "kernel": ["linear", "rbf"],
            }
        )


