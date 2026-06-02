from typing import Any, Dict, List
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from .base import BaseModelWrapper

class LinearDiscriminantAnalysisModel(BaseModelWrapper):
    name = "Linear Discriminant Analysis"
    description = "Linear discriminant analysis classifier."

    def create_estimator(self) -> Any:
        return LinearDiscriminantAnalysis()

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid({"solver": ["svd", "lsqr", "eigen"]})


