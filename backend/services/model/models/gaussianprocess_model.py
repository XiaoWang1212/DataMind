from typing import Any, Dict, List

from sklearn.gaussian_process import GaussianProcessClassifier

from .base import BaseModelWrapper


class GaussianProcessModel(BaseModelWrapper):
    name = "Gaussian Process"
    description = "Gaussian process classifier; ideal for small datasets with uncertainty quantification."

    def create_estimator(self) -> Any:
        return GaussianProcessClassifier(random_state=42, n_jobs=-1)

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "n_restarts_optimizer": [0, 1, 2],
            "warm_start": [True, False],
            "max_iter_predict": [100, 200],
        }
