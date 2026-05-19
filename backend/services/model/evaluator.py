from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold

from .models.base import BaseModelWrapper
from .registry import ModelRegistry


@dataclass
class ModelResult:
    model_name: str
    mean_accuracy: float
    mean_precision: float
    mean_recall: float
    mean_f1: float
    mean_auc: float
    best_params: Dict[str, Any]


class AutomationModelEvaluator:
    """自動化評估器：動態跑所有註冊模型、內外層交叉驗證與比對結果。"""

    def __init__(
        self,
        outer_cv: int = 5,
        inner_cv: int = 3,
        scoring: str = "roc_auc",
        n_jobs: int = -1,
        verbose: int = 0,
        search_method: str = "grid",
        n_iter: int = 50,
        use_all_params: bool = False,
    ) -> None:
        self.outer_cv = outer_cv
        self.inner_cv = inner_cv
        self.scoring = scoring
        self.n_jobs = n_jobs
        self.verbose = verbose
        self.search_method = search_method
        self.n_iter = n_iter
        self.use_all_params = use_all_params
        self.results: List[ModelResult] = []
        self.best_estimators: Dict[str, Any] = {}

    def compare_models(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_names: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        if model_names is None:
            model_names = ModelRegistry.list_models()

        self.results = []
        self.best_estimators = {}

        outer_cv = StratifiedKFold(
            n_splits=self.outer_cv,
            shuffle=True,
            random_state=42,
        )

        for model_name in model_names:
            config = ModelRegistry.get_model_config(model_name)
            if config is None:
                raise ValueError(f"Model '{model_name}' is not registered.")

            fold_metrics = {
                "accuracy": [],
                "precision": [],
                "recall": [],
                "f1": [],
                "auc": [],
            }
            best_params: Dict[str, Any] = {}

            for fold_index, (train_idx, test_idx) in enumerate(
                outer_cv.split(X, y), start=1
            ):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]

                inner_cv = StratifiedKFold(
                    n_splits=self.inner_cv,
                    shuffle=True,
                    random_state=42,
                )
                param_grid = (
                    config.get_all_param_grid()
                    if self.use_all_params
                    else config.get_param_grid()
                )
                if self.search_method == "grid":
                    searcher = GridSearchCV(
                        estimator=config.create_estimator(),
                        param_grid=param_grid,
                        cv=inner_cv,
                        scoring=self.scoring,
                        n_jobs=self.n_jobs,
                        verbose=self.verbose,
                    )
                elif self.search_method == "random":
                    searcher = RandomizedSearchCV(
                        estimator=config.create_estimator(),
                        param_distributions=param_grid,
                        n_iter=self.n_iter,
                        cv=inner_cv,
                        scoring=self.scoring,
                        n_jobs=self.n_jobs,
                        verbose=self.verbose,
                        random_state=42,
                    )
                else:
                    raise ValueError(
                        f"Unsupported search_method '{self.search_method}'. Use 'grid' or 'random'."
                    )
                searcher.fit(X_train, y_train)
                best_estimator = searcher.best_estimator_

                y_pred = best_estimator.predict(X_test)
                y_proba = (
                    best_estimator.predict_proba(X_test)[:, 1]
                    if hasattr(best_estimator, "predict_proba")
                    else y_pred
                )

                fold_metrics["accuracy"].append(accuracy_score(y_test, y_pred))
                fold_metrics["precision"].append(
                    precision_score(y_test, y_pred, zero_division=0)
                )
                fold_metrics["recall"].append(recall_score(y_test, y_pred))
                fold_metrics["f1"].append(f1_score(y_test, y_pred))
                fold_metrics["auc"].append(roc_auc_score(y_test, y_proba))

                if fold_index == 1:
                    best_params = searcher.best_params_

            self.best_estimators[model_name] = best_estimator
            self.results.append(
                ModelResult(
                    model_name=model_name,
                    mean_accuracy=float(np.mean(fold_metrics["accuracy"])),
                    mean_precision=float(np.mean(fold_metrics["precision"])),
                    mean_recall=float(np.mean(fold_metrics["recall"])),
                    mean_f1=float(np.mean(fold_metrics["f1"])),
                    mean_auc=float(np.mean(fold_metrics["auc"])),
                    best_params=best_params,
                )
            )

        return self.to_dataframe()

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Model": result.model_name,
                    "Accuracy": result.mean_accuracy,
                    "Precision": result.mean_precision,
                    "Recall": result.mean_recall,
                    "F1": result.mean_f1,
                    "AUC": result.mean_auc,
                    "Best Params": result.best_params,
                }
                for result in self.results
            ]
        )

    def add_custom_model(self, wrapper: "BaseModelWrapper") -> None:
        ModelRegistry.register_model(wrapper)

    def remove_model(self, model_name: str) -> None:
        ModelRegistry.unregister_model(model_name)
