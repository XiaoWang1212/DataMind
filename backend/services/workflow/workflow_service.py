from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix as sk_confusion_matrix
from sklearn.model_selection import (
    GridSearchCV,
    GroupKFold,
    KFold,
    LeaveOneOut,
    RandomizedSearchCV,
    RepeatedKFold,
    ShuffleSplit,
    StratifiedKFold,
    StratifiedShuffleSplit,
    train_test_split,
)

from services.model.registry import ModelRegistry
from .feature_engineering_service import apply_feature_engineering_pipeline_for_split
from .preprocess_service import apply_preprocess_pipeline_for_split, generate_preprocess_variants
from .resampling_service import apply_resampling, describe_class_distribution
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
    def load_data(data_path: str) -> pd.DataFrame:
        file_path = Path(data_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        suffix = file_path.suffix.lower()

        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(file_path)

        # CSV with encoding fallback
        try:
            return pd.read_csv(file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="cp950")

    # Keep legacy name as alias
    @classmethod
    def load_csv_data(cls, data_path: str) -> pd.DataFrame:
        return cls.load_data(data_path)

    @staticmethod
    def _prepare_categorical(
        train_df: pd.DataFrame, test_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """One-hot encode any remaining object/category columns, fit on train only."""
        object_cols = train_df.select_dtypes(include=["object", "category"]).columns.tolist()
        if not object_cols:
            return train_df, test_df

        train_dummies = pd.get_dummies(train_df[object_cols], drop_first=True)
        test_dummies = pd.get_dummies(test_df[object_cols], drop_first=True)

        # Align test to train columns
        for col in train_dummies.columns:
            if col not in test_dummies.columns:
                test_dummies[col] = 0
        test_dummies = test_dummies[train_dummies.columns]

        train_out = pd.concat(
            [train_df.drop(columns=object_cols), train_dummies], axis=1
        )
        test_out = pd.concat(
            [test_df.drop(columns=object_cols), test_dummies], axis=1
        )
        return train_out, test_out

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

    @staticmethod
    def _extract_feature_importance(
        estimator: Any, feature_names: List[str]
    ) -> Optional[List[Dict[str, Any]]]:
        if not feature_names:
            return None

        importance_values = None
        if hasattr(estimator, "feature_importances_"):
            importance_values = np.asarray(getattr(estimator, "feature_importances_"))
        elif hasattr(estimator, "coef_"):
            coef = np.asarray(getattr(estimator, "coef_"))
            importance_values = (
                np.abs(coef) if coef.ndim == 1 else np.mean(np.abs(coef), axis=0)
            )

        if importance_values is None or importance_values.shape[0] != len(feature_names):
            return None

        return sorted(
            [
                {"feature": f, "importance": float(v)}
                for f, v in zip(feature_names, importance_values)
            ],
            key=lambda x: x["importance"],
            reverse=True,
        )

    @staticmethod
    def _build_confusion_matrix(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]:
        """算 NxN 混淆矩陣，不寫死二分類——sklearn 本來就支援任意類別數。"""
        labels = sorted(pd.unique(pd.concat([y_true, y_pred]).dropna()), key=str)
        matrix = sk_confusion_matrix(y_true, y_pred, labels=labels)
        return {
            "labels": [str(label) for label in labels],
            "matrix": matrix.tolist(),
        }

    @classmethod
    def _generate_resampling_splits(
        cls,
        X: pd.DataFrame,
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
            if group_column in X.columns:
                groups = X[group_column]
            else:
                raise ValueError(
                    f"Group column '{group_column}' not found in features"
                )

        if method in {"test_on_test", "test_on_train"}:
            try:
                X_tr, X_te, y_tr, y_te = train_test_split(
                    X, y,
                    train_size=train_size,
                    test_size=test_size,
                    stratify=y if stratified and len(pd.unique(y)) > 1 else None,
                    shuffle=shuffle,
                    random_state=random_state,
                )
            except ValueError:
                X_tr, X_te, y_tr, y_te = train_test_split(
                    X, y,
                    train_size=train_size,
                    test_size=test_size,
                    shuffle=shuffle,
                    random_state=random_state,
                )

            eval_idx = X_tr.index.tolist() if method == "test_on_train" else X_te.index.tolist()
            return [
                {
                    "name": method,
                    "train_index": X_tr.index.tolist(),
                    "test_index": eval_idx,
                    "config": config,
                }
            ]

        if method == "k_fold":
            splitter = (
                StratifiedKFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)
                if stratified and len(pd.unique(y)) > 1
                else KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)
            )
            split_source = y if stratified and len(pd.unique(y)) > 1 else X
        elif method == "group_k_fold":
            if groups is None:
                raise ValueError("group_column is required for group cross-validation")
            splitter = GroupKFold(n_splits=n_splits)
            split_source = X
        elif method == "leave_one_out":
            splitter = LeaveOneOut()
            split_source = X
        else:  # random_sampling
            splitter = (
                StratifiedShuffleSplit(
                    n_splits=n_repeats,
                    train_size=train_size,
                    test_size=test_size,
                    random_state=random_state,
                )
                if stratified and len(pd.unique(y)) > 1
                else ShuffleSplit(
                    n_splits=n_repeats,
                    train_size=train_size,
                    test_size=test_size,
                    random_state=random_state,
                )
            )
            split_source = y if stratified and len(pd.unique(y)) > 1 else X

        splits: List[Dict[str, Any]] = []
        iterator = (
            splitter.split(X, X, groups)
            if method == "group_k_fold"
            else splitter.split(X, split_source)
        )
        for i, (train_idx, test_idx) in enumerate(iterator):
            splits.append(
                {
                    "name": f"{method}_{i + 1}",
                    "train_index": train_idx.tolist(),
                    "test_index": test_idx.tolist(),
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
        feature_engineering_pipelines: Optional[List[List[Dict[str, Any]]]] = None,
        column_config: Optional[List[Dict[str, Any]]] = None,
        # Resampling
        resampling_method: str = "none",
        resampling_config: Optional[Dict[str, Any]] = None,
        # Hyperparameter tuning
        tuning_method: str = "none",
        tuning_cv: int = 3,
        tuning_n_iter: int = 20,
        tuning_scoring: str = "roc_auc",
        # Confidence intervals
        compute_ci: bool = False,
        ci_n_bootstrap: int = 1000,
        # Legacy
        train_size: float = 0.7,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        df = cls.load_data(data_path)

        if target_col not in df.columns:
            raise ValueError(f"Target column not found: {target_col}")

        y = df[target_col]
        X = df.drop(columns=[target_col])

        # Drop columns marked as skip or meta in column_config
        if column_config:
            exclude_roles = {"skip", "meta"}
            skip_cols = [
                item["name"]
                for item in column_config
                if isinstance(item, dict) and item.get("role") in exclude_roles
                and isinstance(item.get("name"), str)
            ]
            X = X.drop(columns=[c for c in skip_cols if c in X.columns], errors="ignore")

        if X.empty:
            raise ValueError("Feature matrix is empty after dropping the target column")

        if not preprocess_pipelines:
            preprocess_pipelines = [[]]
        if not feature_engineering_pipelines:
            feature_engineering_pipelines = [[]]

        validation_config = validation_config or {"method": "test_on_test"}
        resampling_config = resampling_config or {}
        results: List[Dict[str, Any]] = []

        class_dist = describe_class_distribution(y)

        # Generate splits once (on raw X to preserve indices)
        split_definitions = cls._generate_resampling_splits(X, y, validation_config)

        for pipeline_index, pipeline_steps in enumerate(preprocess_pipelines):
            feature_steps = (
                feature_engineering_pipelines[pipeline_index]
                if pipeline_index < len(feature_engineering_pipelines)
                else []
            )

            for model_name in model_names:
                model_config = ModelRegistry.get_model_config(model_name)
                if model_config is None:
                    results.append(
                        {
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "error": f"Unknown model name: {model_name}",
                        }
                    )
                    continue

                for split_def in split_definitions:
                    train_idx = split_def["train_index"]
                    test_idx = split_def["test_index"]

                    X_train_raw = X.iloc[train_idx]
                    X_test_raw = X.iloc[test_idx]
                    y_train = y.iloc[train_idx]
                    y_test = y.iloc[test_idx]

                    # ── 1. Preprocessing (fit on train only — no leakage) ───────
                    X_train, X_test = apply_preprocess_pipeline_for_split(
                        X_train_raw, X_test_raw, pipeline_steps
                    )

                    # ── 2. Encode remaining categoricals (fit on train only) ────
                    X_train, X_test = cls._prepare_categorical(X_train, X_test)

                    if X_train.empty:
                        results.append(
                            {
                                "preprocess_pipeline_index": pipeline_index,
                                "model_name": model_name,
                                "split_name": split_def["name"],
                                "error": "Feature matrix empty after preprocessing",
                            }
                        )
                        continue

                    # ── 3. Feature engineering (fit on train only) ─────────────
                    if feature_steps:
                        X_train, X_test = apply_feature_engineering_pipeline_for_split(
                            X_train, X_test, feature_steps, target_train=y_train
                        )

                    # ── 4. Resampling (train only) ─────────────────────────────
                    if resampling_method != "none":
                        try:
                            X_train, y_train = apply_resampling(
                                X_train, y_train,
                                method=resampling_method,
                                config=resampling_config,
                            )
                        except Exception as exc:
                            results.append(
                                {
                                    "preprocess_pipeline_index": pipeline_index,
                                    "model_name": model_name,
                                    "split_name": split_def["name"],
                                    "error": f"Resampling failed: {exc}",
                                }
                            )
                            continue

                    # ── 5. Hyperparameter tuning OR plain fit ──────────────────
                    estimator = model_config.create_estimator()
                    best_params: Dict[str, Any] = {}

                    if tuning_method in {"grid", "random"}:
                        param_grid = model_config.get_param_grid()
                        if param_grid:
                            inner_cv = StratifiedKFold(
                                n_splits=tuning_cv, shuffle=True, random_state=42
                            )
                            if tuning_method == "grid":
                                searcher = GridSearchCV(
                                    estimator=estimator,
                                    param_grid=param_grid,
                                    cv=inner_cv,
                                    scoring=tuning_scoring,
                                    n_jobs=-1,
                                    error_score="raise",
                                )
                            else:
                                searcher = RandomizedSearchCV(
                                    estimator=estimator,
                                    param_distributions=param_grid,
                                    n_iter=tuning_n_iter,
                                    cv=inner_cv,
                                    scoring=tuning_scoring,
                                    n_jobs=-1,
                                    random_state=42,
                                    error_score="raise",
                                )
                            try:
                                searcher.fit(X_train, y_train)
                                estimator = searcher.best_estimator_
                                best_params = searcher.best_params_
                            except Exception as exc:
                                # Tuning failed — fall back to default fit
                                estimator = model_config.create_estimator()
                                estimator.fit(X_train, y_train)
                                best_params = {"tuning_error": str(exc)}
                        else:
                            estimator.fit(X_train, y_train)
                    else:
                        estimator.fit(X_train, y_train)

                    # ── 6. Predict ─────────────────────────────────────────────
                    y_pred = pd.Series(estimator.predict(X_test), index=y_test.index)
                    y_score = None
                    if hasattr(estimator, "predict_proba"):
                        try:
                            proba = estimator.predict_proba(X_test)
                            classes = getattr(estimator, "classes_", None)
                            y_score = {
                                "proba": proba,
                                "classes": classes.tolist() if classes is not None else None,
                            }
                        except Exception:
                            y_score = None

                    # ── 7. Evaluate metrics ────────────────────────────────────
                    metrics = evaluate_metrics(
                        y_test, y_pred, y_score, score_variants,
                        compute_ci=compute_ci,
                        ci_n_bootstrap=ci_n_bootstrap,
                    )

                    results.append(
                        {
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "preprocess_steps": pipeline_steps,
                            "feature_engineering_steps": feature_steps,
                            "split_name": split_def["name"],
                            "validation_config": split_def["config"],
                            "resampling_method": resampling_method,
                            "best_params": best_params,
                            "metrics": metrics,
                            "feature_importance": cls._extract_feature_importance(
                                estimator, list(X_train.columns)
                            ),
                            "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                            "feature_count": int(X_train.shape[1]),
                            "row_count": int(X_train.shape[0]),
                        }
                    )

        return {
            "success": True,
            "results": results,
            "preprocess_variants": preprocess_pipelines,
            "score_variants": score_variants,
            "class_distribution": class_dist,
        }

    @classmethod
    def execute_workflow_stream(
        cls,
        data_path: str,
        target_col: str,
        preprocess_pipelines: List[List[Dict[str, Any]]],
        model_names: List[str],
        score_variants: List[Dict[str, Any]],
        validation_config: Optional[Dict[str, Any]] = None,
        feature_engineering_pipelines: Optional[List[List[Dict[str, Any]]]] = None,
        column_config: Optional[List[Dict[str, Any]]] = None,
        resampling_method: str = "none",
        resampling_config: Optional[Dict[str, Any]] = None,
        tuning_method: str = "none",
        tuning_cv: int = 3,
        tuning_n_iter: int = 20,
        tuning_scoring: str = "roc_auc",
        compute_ci: bool = False,
        ci_n_bootstrap: int = 1000,
        train_size: float = 0.7,
        random_state: int = 42,
    ) -> Generator[Dict[str, Any], None, None]:
        """每個 model 跑完所有 splits 後立即 yield 結果，最後 yield 完整摘要。"""
        df = cls.load_data(data_path)

        if target_col not in df.columns:
            raise ValueError(f"Target column not found: {target_col}")

        y = df[target_col]
        X = df.drop(columns=[target_col])

        if column_config:
            exclude_roles = {"skip", "meta"}
            skip_cols = [
                item["name"]
                for item in column_config
                if isinstance(item, dict) and item.get("role") in exclude_roles
                and isinstance(item.get("name"), str)
            ]
            X = X.drop(columns=[c for c in skip_cols if c in X.columns], errors="ignore")

        if X.empty:
            raise ValueError("Feature matrix is empty after dropping the target column")

        if not preprocess_pipelines:
            preprocess_pipelines = [[]]
        if not feature_engineering_pipelines:
            feature_engineering_pipelines = [[]]

        validation_config = validation_config or {"method": "test_on_test"}
        resampling_config = resampling_config or {}
        class_dist = describe_class_distribution(y)
        split_definitions = cls._generate_resampling_splits(X, y, validation_config)

        all_results: List[Dict[str, Any]] = []

        for pipeline_index, pipeline_steps in enumerate(preprocess_pipelines):
            feature_steps = (
                feature_engineering_pipelines[pipeline_index]
                if pipeline_index < len(feature_engineering_pipelines)
                else []
            )

            for model_name in model_names:
                model_results: List[Dict[str, Any]] = []

                model_config = ModelRegistry.get_model_config(model_name)
                if model_config is None:
                    model_results.append({
                        "preprocess_pipeline_index": pipeline_index,
                        "model_name": model_name,
                        "error": f"Unknown model name: {model_name}",
                    })
                    all_results.extend(model_results)
                    yield {"type": "model_done", "model_name": model_name, "results": model_results}
                    continue

                for split_def in split_definitions:
                    train_idx = split_def["train_index"]
                    test_idx = split_def["test_index"]

                    X_train_raw = X.iloc[train_idx]
                    X_test_raw = X.iloc[test_idx]
                    y_train = y.iloc[train_idx]
                    y_test = y.iloc[test_idx]

                    X_train, X_test = apply_preprocess_pipeline_for_split(
                        X_train_raw, X_test_raw, pipeline_steps
                    )
                    X_train, X_test = cls._prepare_categorical(X_train, X_test)

                    if X_train.empty:
                        model_results.append({
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "split_name": split_def["name"],
                            "error": "Feature matrix empty after preprocessing",
                        })
                        continue

                    if feature_steps:
                        X_train, X_test = apply_feature_engineering_pipeline_for_split(
                            X_train, X_test, feature_steps, target_train=y_train
                        )

                    if resampling_method != "none":
                        try:
                            X_train, y_train = apply_resampling(
                                X_train, y_train,
                                method=resampling_method,
                                config=resampling_config,
                            )
                        except Exception as exc:
                            model_results.append({
                                "preprocess_pipeline_index": pipeline_index,
                                "model_name": model_name,
                                "split_name": split_def["name"],
                                "error": f"Resampling failed: {exc}",
                            })
                            continue

                    estimator = model_config.create_estimator()
                    best_params: Dict[str, Any] = {}

                    if tuning_method in {"grid", "random"}:
                        param_grid = model_config.get_param_grid()
                        if param_grid:
                            inner_cv = StratifiedKFold(n_splits=tuning_cv, shuffle=True, random_state=42)
                            SearchClass = GridSearchCV if tuning_method == "grid" else RandomizedSearchCV
                            search_kwargs: Dict[str, Any] = dict(
                                estimator=estimator,
                                cv=inner_cv,
                                scoring=tuning_scoring,
                                n_jobs=-1,
                                error_score="raise",
                            )
                            if tuning_method == "grid":
                                search_kwargs["param_grid"] = param_grid
                            else:
                                search_kwargs["param_distributions"] = param_grid
                                search_kwargs["n_iter"] = tuning_n_iter
                                search_kwargs["random_state"] = 42
                            try:
                                searcher = SearchClass(**search_kwargs)
                                searcher.fit(X_train, y_train)
                                estimator = searcher.best_estimator_
                                best_params = searcher.best_params_
                            except Exception as exc:
                                estimator = model_config.create_estimator()
                                estimator.fit(X_train, y_train)
                                best_params = {"tuning_error": str(exc)}
                        else:
                            estimator.fit(X_train, y_train)
                    else:
                        estimator.fit(X_train, y_train)

                    y_pred = pd.Series(estimator.predict(X_test), index=y_test.index)
                    y_score = None
                    if hasattr(estimator, "predict_proba"):
                        try:
                            proba = estimator.predict_proba(X_test)
                            classes = getattr(estimator, "classes_", None)
                            y_score = {
                                "proba": proba,
                                "classes": classes.tolist() if classes is not None else None,
                            }
                        except Exception:
                            y_score = None

                    metrics = evaluate_metrics(
                        y_test, y_pred, y_score, score_variants,
                        compute_ci=compute_ci,
                        ci_n_bootstrap=ci_n_bootstrap,
                    )

                    model_results.append({
                        "preprocess_pipeline_index": pipeline_index,
                        "model_name": model_name,
                        "preprocess_steps": pipeline_steps,
                        "feature_engineering_steps": feature_steps,
                        "split_name": split_def["name"],
                        "validation_config": split_def["config"],
                        "resampling_method": resampling_method,
                        "best_params": best_params,
                        "metrics": metrics,
                        "feature_importance": cls._extract_feature_importance(
                            estimator, list(X_train.columns)
                        ),
                        "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                        "feature_count": int(X_train.shape[1]),
                        "row_count": int(X_train.shape[0]),
                    })

                all_results.extend(model_results)
                yield {"type": "model_done", "model_name": model_name, "results": model_results}

        yield {
            "type": "done",
            "success": True,
            "results": all_results,
            "preprocess_variants": preprocess_pipelines,
            "score_variants": score_variants,
            "class_distribution": class_dist,
        }

    @staticmethod
    def list_registered_models() -> List[str]:
        return ModelRegistry.list_models()
