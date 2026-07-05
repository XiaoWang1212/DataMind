from typing import Any, Dict, List

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from .base import BaseModelWrapper


class VotingModel(BaseModelWrapper):
    name = "Voting Classifier"
    description = "Soft-voting ensemble of Logistic Regression, Random Forest, and SVM."

    def create_estimator(self) -> Any:
        return VotingClassifier(
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
                ("svc", SVC(probability=True, random_state=42)),
            ],
            voting="soft",
            n_jobs=-1,
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return {
            "weights": [None, [1, 2, 1], [2, 1, 1], [1, 1, 2]],
            "lr__C": [0.1, 1.0, 10.0],
            "rf__n_estimators": [50, 100, 200],
            "svc__C": [0.1, 1.0, 10.0],
        }
