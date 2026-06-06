from typing import Any, Dict, List

from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression

from .base import BaseModelWrapper


class StackingModel(BaseModelWrapper):
    name = "Stacking Classifier"
    description = "Stacking ensemble with LR, RF, ExtraTrees base estimators and LR as meta-learner."

    def create_estimator(self) -> Any:
        return StackingClassifier(
            estimators=[
                (
                    "lr",
                    LogisticRegression(
                        max_iter=1000, class_weight="balanced", random_state=42
                    ),
                ),
                (
                    "rf",
                    RandomForestClassifier(
                        n_estimators=100,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
                (
                    "et",
                    ExtraTreesClassifier(
                        n_estimators=100,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ],
            final_estimator=LogisticRegression(max_iter=1000, random_state=42),
            passthrough=False,
            n_jobs=-1,
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "passthrough": [True, False],
            "final_estimator__C": [0.1, 1.0, 10.0],
        }
