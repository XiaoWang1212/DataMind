from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import (
    GroupKFold,
    KFold,
    LeaveOneOut,
    RepeatedKFold,
    ShuffleSplit,
    StratifiedKFold,
    StratifiedShuffleSplit,
    train_test_split,
)

from services.model.registry import ModelRegistry
from .preprocess_service import apply_preprocess_pipeline, generate_preprocess_variants
from .test_score_service import evaluate_metrics, generate_score_variants


class WorkflowService:
    @staticmethod
    def generate_preprocess_variants(
        step_groups: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return generate_preprocess_variants(step_groups)

    @staticmethod
    def generate_score_variants(
        score_groups: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return generate_score_variants(score_groups)

    @staticmethod
    def load_csv_data(data_path: str) -> pd.DataFrame:
        file_path = Path(data_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        try:
            return pd.read_csv(file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="cp950")

    @staticmethod
    def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
        object_columns = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()
        if object_columns:
            df = pd.get_dummies(df, columns=object_columns, drop_first=True)
        return df

    @staticmethod
    def _safe_score_array(value: Optional[Any]) -> Optional[np.ndarray]:
        if value is None:
            return None

        try:
            arr = np.asarray(value, dtype=float)
        except Exception:
            return None

        if arr.ndim == 1:
            return arr
        if arr.ndim == 2 and arr.shape[1] == 1:
            return arr.ravel()
        return None

    @staticmethod
    def _normalize_validation_config(config: Dict[str, Any]) -> Dict[str, Any]:
        method = str(config.get("method", "test_on_test")).lower()
        method_aliases = {
            "test on test data": "test_on_test",
            "test on train data": "test_on_train",
            "cross validation": "k_fold",
            "cross validation by feature": "group_k_fold",
            "random sampling": "random_sampling",
            "leave one out": "leave_one_out",
        }
        method = method_aliases.get(method, method)
        if method not in {
            "test_on_test",
            "test_on_train",
            "k_fold",
            "group_k_fold",
            "random_sampling",
            "leave_one_out",
        }:
            method = "test_on_test"

        return {
            "method": method,
            "n_splits": int(config.get("n_splits", 5)),
            "n_repeats": int(config.get("n_repeats", 1)),
            "train_size": float(config.get("train_size", 0.7)),
            "test_size": config.get("test_size"),
            "stratified": bool(config.get("stratified", True)),
            "group_column": config.get("group_column"),
            "shuffle": bool(config.get("shuffle", True)),
            "random_state": int(config.get("random_state", 42)),
        }

    @classmethod
    def _generate_resampling_splits(
        cls,
        processed: pd.DataFrame,
        y: pd.Series,
        validation_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        config = cls._normalize_validation_config(validation_config or {})
        method = config["method"]
        n_splits = config["n_splits"]
        n_repeats = config["n_repeats"]
        train_size = config["train_size"]
        test_size = config["test_size"]
        stratified = config["stratified"]
        group_column = config["group_column"]
        shuffle = config["shuffle"]
        random_state = config["random_state"]

        if test_size is None:
            test_size = 1.0 - train_size

        groups = None
        if group_column:
            if group_column in processed.columns:
                groups = processed[group_column]
            else:
                raise ValueError(
                    f"Group column '{group_column}' not found in features for group cross-validation"
                )

        if method in {"test_on_test", "test_on_train"}:
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    processed,
                    y,
                    train_size=train_size,
                    test_size=test_size,
                    stratify=y if stratified and len(pd.unique(y)) > 1 else None,
                    shuffle=shuffle,
                    random_state=random_state,
                )
            except ValueError:
                X_train, X_test, y_train, y_test = train_test_split(
                    processed,
                    y,
                    train_size=train_size,
                    test_size=test_size,
                    shuffle=shuffle,
                    random_state=random_state,
                )

            if method == "test_on_train":
                return [
                    {
                        "name": "test_on_train",
                        "train_index": X_train.index.to_list(),
                        "test_index": X_train.index.to_list(),
                        "config": config,
                    }
                ]

            return [
                {
                    "name": "test_on_test",
                    "train_index": X_train.index.to_list(),
                    "test_index": X_test.index.to_list(),
                    "config": config,
                }
            ]

        if method == "k_fold":
            if stratified and len(pd.unique(y)) > 1:
                splitter = StratifiedKFold(
                    n_splits=n_splits,
                    shuffle=shuffle,
                    random_state=random_state,
                )
                split_source = y
            else:
                splitter = KFold(
                    n_splits=n_splits,
                    shuffle=shuffle,
                    random_state=random_state,
                )
                split_source = processed
        elif method == "group_k_fold":
            if groups is None:
                raise ValueError("group_column is required for group cross-validation")
            splitter = GroupKFold(n_splits=n_splits)
            split_source = processed
        elif method == "leave_one_out":
            splitter = LeaveOneOut()
            split_source = processed
        else:
            if stratified and len(pd.unique(y)) > 1:
                splitter = StratifiedShuffleSplit(
                    n_splits=n_repeats,
                    train_size=train_size,
                    test_size=test_size,
                    random_state=random_state,
                )
                split_source = y
            else:
                splitter = ShuffleSplit(
                    n_splits=n_repeats,
                    train_size=train_size,
                    test_size=test_size,
                    random_state=random_state,
                )
                split_source = processed

        splits: List[Dict[str, Any]] = []
        if method == "group_k_fold":
            iterator = splitter.split(processed, processed, groups)
        else:
            iterator = splitter.split(processed, split_source)

        for split_index, (train_index, test_index) in enumerate(iterator):
            splits.append(
                {
                    "name": f"{method}_{split_index + 1}",
                    "train_index": train_index.tolist(),
                    "test_index": test_index.tolist(),
                    "config": config,
                }
            )

        return splits

    @classmethod
    def execute_workflow(
        cls,
        data_path: str,
        target_col: str,
        preprocess_pipelines: List[List[Dict[str, Any]]],
        model_names: List[str],
        score_variants: List[Dict[str, Any]],
        validation_config: Optional[Dict[str, Any]] = None,
        train_size: float = 0.7,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        df = cls.load_csv_data(data_path)

        if target_col not in df.columns:
            raise ValueError(f"Target column not found: {target_col}")

        y = df[target_col]
        X = df.drop(columns=[target_col])

        if X.empty:
            raise ValueError("Feature matrix is empty after dropping the target column")

        results: List[Dict[str, Any]] = []
        validation_config = validation_config or {"method": "test_on_test"}

        if not preprocess_pipelines:
            preprocess_pipelines = [[]]

        for pipeline_index, pipeline_steps in enumerate(preprocess_pipelines):
            processed = apply_preprocess_pipeline(X.copy(), pipeline_steps)
            processed = cls._prepare_features(processed)

            if processed.empty:
                raise ValueError(
                    f"Preprocessed feature set is empty for pipeline {pipeline_index}"
                )

            split_definitions = cls._generate_resampling_splits(
                processed, y, validation_config
            )

            for model_name in model_names:
                model_config = ModelRegistry.get_model_config(model_name)
                if model_config is None:
                    results.append(
                        {
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "error": "Unknown model name",
                        }
                    )
                    continue

                for split_definition in split_definitions:
                    estimator = model_config.create_estimator()
                    train_idx = split_definition["train_index"]
                    test_idx = split_definition["test_index"]

                    X_train = processed.iloc[train_idx]
                    X_test = processed.iloc[test_idx]
                    y_train = y.iloc[train_idx]
                    y_test = y.iloc[test_idx]

                    estimator.fit(X_train, y_train)
                    y_pred = pd.Series(estimator.predict(X_test), index=y_test.index)
                    y_score = None
                    if hasattr(estimator, "predict_proba"):
                        try:
                            y_score = cls._safe_score_array(
                                estimator.predict_proba(X_test)[:, 1]
                            )
                        except Exception:
                            y_score = None

                    metrics = evaluate_metrics(y_test, y_pred, y_score, score_variants)
                    results.append(
                        {
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "pipeline_steps": pipeline_steps,
                            "split_name": split_definition["name"],
                            "validation_config": split_definition["config"],
                            "metrics": metrics,
                            "feature_count": int(processed.shape[1]),
                            "row_count": int(processed.shape[0]),
                        }
                    )

        return {
            "success": True,
            "results": results,
            "preprocess_variants": preprocess_pipelines,
            "score_variants": score_variants,
        }

    @staticmethod
    def list_registered_models() -> List[str]:
        return ModelRegistry.list_models()
