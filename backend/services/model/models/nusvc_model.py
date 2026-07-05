from typing import Any, Dict, List

from sklearn.svm import NuSVC

from .base import BaseModelWrapper


class NuSVCModel(BaseModelWrapper):
    name = "Nu-SVC"
    description = "Nu-support vector classification; nu controls the upper bound on training error fraction."

    def create_estimator(self) -> Any:
        return NuSVC(probability=True, random_state=42)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "nu": [0.1, 0.25, 0.5],
            "kernel": ["linear", "rbf"],
            "class_weight": ["balanced", None],
        }
