from typing import Any, Dict, List
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from .base import BaseModelWrapper

class QuadraticDiscriminantAnalysisModel(BaseModelWrapper):
    name = "Quadratic Discriminant Analysis"
    description = "Quadratic discriminant analysis classifier."

    def create_estimator(self) -> Any:
        return QuadraticDiscriminantAnalysis()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid({"reg_param": [0.0, 0.1, 0.5]})


