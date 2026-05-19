from typing import Any, Dict, List
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from .base import BaseModelWrapper

class CalibratedClassifierModel(BaseModelWrapper):
    name = "Calibrated Classifier"
    description = (
        "Probability-calibrated classifier for improved probability estimates."
    )

    def create_estimator(self) -> Any:
        return CalibratedClassifierCV(
            estimator=LogisticRegression(max_iter=2000),
            cv=3,
            method="sigmoid",
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "cv": [2, 3, 5],
                "method": ["sigmoid", "isotonic"],
            }
        )


