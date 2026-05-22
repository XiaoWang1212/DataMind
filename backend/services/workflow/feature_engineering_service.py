from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif, VarianceThreshold
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

FEATURE_ENGINEERING_STEP_TYPES = {
    "discretize_continuous",
    "continuize_discrete",
    "impute_missing",
    "select_relevant_features",
    "select_random_features",
    "normalize_features",
    "randomize_rows",
    "remove_sparse_features",
    "pca",
    "cur_decomposition",
}


def _discretize_continuous(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    bins = int(step.get("bins", 5))
    labels = step.get("labels")
    numeric_columns = [
        col
        for col in (columns or df.select_dtypes(include=["number"]).columns.tolist())
        if col in df.columns
    ]
    if not numeric_columns:
        return df

    result = df.copy()
    for column in numeric_columns:
        result[column] = pd.cut(
            result[column],
            bins=bins,
            labels=labels,
            duplicates="drop",
        )
    return result


def _continuize_discrete(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    discrete_columns = [
        col
        for col in (
            columns or df.select_dtypes(include=["object", "category"]).columns.tolist()
        )
        if col in df.columns
    ]
    if not discrete_columns:
        return df

    result = df.copy()
    for column in discrete_columns:
        if result[column].dtype.name == "category" or result[column].dtype == object:
            encoder = LabelEncoder()
            result[column] = encoder.fit_transform(result[column].astype(str))
    return result


def _impute_missing(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    strategy = step.get("strategy", "constant")
    value = step.get("value", 0)
    result = df.copy()

    if not columns:
        columns = result.columns.tolist()

    for column in columns:
        if column not in result.columns:
            continue
        if strategy == "mean" and pd.api.types.is_numeric_dtype(result[column]):
            result[column] = result[column].fillna(result[column].mean())
        elif strategy == "median" and pd.api.types.is_numeric_dtype(result[column]):
            result[column] = result[column].fillna(result[column].median())
        elif strategy == "mode":
            result[column] = result[column].fillna(
                result[column].mode().iloc[0]
                if not result[column].mode().empty
                else value
            )
        else:
            result[column] = result[column].fillna(value)

    return result


def _select_relevant_feature_names(
    df: pd.DataFrame,
    step: Dict[str, Any],
    target: Optional[pd.Series] = None,
) -> List[str]:
    k = int(step.get("k", min(len(df.columns), 10)))
    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        return []

    if target is None or len(target) != len(df):
        selector = VarianceThreshold(
            threshold=float(step.get("variance_threshold", 0.0))
        )
        selector.fit(numeric_df)
        mask = selector.get_support()
        numeric_cols = numeric_df.columns.tolist()
        selected = [col for include, col in zip(mask, numeric_cols) if include][:k]
        return selected

    selector = SelectKBest(score_func=f_classif, k=min(k, numeric_df.shape[1]))
    selector.fit(numeric_df, target)
    return numeric_df.columns[selector.get_support()].tolist()


def _select_relevant_features(
    df: pd.DataFrame,
    step: Dict[str, Any],
    target: Optional[pd.Series] = None,
) -> pd.DataFrame:
    selected = _select_relevant_feature_names(df, step, target=target)
    return df[[col for col in selected if col in df.columns]]


def _select_random_features(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    k = int(step.get("k", min(len(df.columns), 5)))
    random_state = step.get("random_state")
    return df.sample(n=k, axis=1, random_state=random_state)


def _normalize_features(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    numeric = df.select_dtypes(include=["number"]).columns.tolist()
    target_columns = [col for col in (columns or numeric) if col in df.columns]
    if not target_columns:
        return df

    scaler = MinMaxScaler()
    result = df.copy()
    result[target_columns] = scaler.fit_transform(result[target_columns])
    return result


def _randomize_rows(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    frac = 1.0
    random_state = step.get("random_state")
    return df.sample(frac=frac, random_state=random_state).reset_index(drop=True)


def _remove_sparse_features(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    threshold = float(step.get("threshold", 0.9))
    numeric = df.select_dtypes(include=["number"])
    keep_columns = [
        col for col in numeric.columns if numeric[col].notna().mean() >= 1.0 - threshold
    ]
    return df[keep_columns]


def _pca(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    n_components = int(step.get("n_components", min(len(df.columns), 2)))
    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        return df

    pca = PCA(n_components=min(n_components, numeric_df.shape[1]))
    transformed = pca.fit_transform(numeric_df)
    columns = [f"pca_{i + 1}" for i in range(transformed.shape[1])]
    return pd.DataFrame(transformed, columns=columns, index=df.index)


def _cur_decomposition(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    n_components = int(step.get("n_components", min(len(df.columns), 2)))
    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        return df

    U, s, Vt = np.linalg.svd(numeric_df.fillna(0).values, full_matrices=False)
    U = U[:, :n_components]
    s = s[:n_components]
    transformed = U * s
    columns = [f"cur_{i + 1}" for i in range(transformed.shape[1])]
    return pd.DataFrame(transformed, columns=columns, index=df.index)


def apply_feature_engineering_pipeline(
    df: pd.DataFrame,
    pipeline_steps: List[Dict[str, Any]],
    target: Optional[pd.Series] = None,
) -> pd.DataFrame:
    result = df.copy()

    for step in pipeline_steps:
        step_type = step.get("type")
        if step_type not in FEATURE_ENGINEERING_STEP_TYPES:
            continue

        if step_type == "discretize_continuous":
            result = _discretize_continuous(result, step)
        elif step_type == "continuize_discrete":
            result = _continuize_discrete(result, step)
        elif step_type == "impute_missing":
            result = _impute_missing(result, step)
        elif step_type == "select_relevant_features":
            result = _select_relevant_features(result, step, target=target)
        elif step_type == "select_random_features":
            result = _select_random_features(result, step)
        elif step_type == "normalize_features":
            result = _normalize_features(result, step)
        elif step_type == "randomize_rows":
            result = _randomize_rows(result, step)
        elif step_type == "remove_sparse_features":
            result = _remove_sparse_features(result, step)
        elif step_type == "pca":
            result = _pca(result, step)
        elif step_type == "cur_decomposition":
            result = _cur_decomposition(result, step)

    return result


def apply_feature_engineering_pipeline_for_split(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pipeline_steps: List[Dict[str, Any]],
    target_train: Optional[pd.Series] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_result = train_df.copy()
    test_result = test_df.copy()

    for step in pipeline_steps:
        step_type = step.get("type")
        if step_type not in FEATURE_ENGINEERING_STEP_TYPES:
            continue

        if step_type == "discretize_continuous":
            train_result = _discretize_continuous(train_result, step)
            test_result = _discretize_continuous(test_result, step)
        elif step_type == "continuize_discrete":
            train_result = _continuize_discrete(train_result, step)
            test_result = _continuize_discrete(test_result, step)
        elif step_type == "impute_missing":
            train_result = _impute_missing(train_result, step)
            test_result = _impute_missing(test_result, step)
        elif step_type == "select_relevant_features":
            selected = _select_relevant_feature_names(
                train_result, step, target=target_train
            )
            train_result = train_result[
                [col for col in selected if col in train_result.columns]
            ]
            test_result = test_result[
                [col for col in selected if col in test_result.columns]
            ]
        elif step_type == "select_random_features":
            train_result = _select_random_features(train_result, step)
            test_result = _select_random_features(test_result, step)
        elif step_type == "normalize_features":
            train_result = _normalize_features(train_result, step)
            test_result = _normalize_features(test_result, step)
        elif step_type == "randomize_rows":
            train_result = _randomize_rows(train_result, step)
            test_result = _randomize_rows(test_result, step)
        elif step_type == "remove_sparse_features":
            train_result = _remove_sparse_features(train_result, step)
            test_result = _remove_sparse_features(test_result, step)
        elif step_type == "pca":
            train_result = _pca(train_result, step)
            test_result = _pca(test_result, step)
        elif step_type == "cur_decomposition":
            train_result = _cur_decomposition(train_result, step)
            test_result = _cur_decomposition(test_result, step)

    return train_result, test_result


def generate_feature_engineering_variants(
    step_groups: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not step_groups:
        return []

    groups = []
    for group in step_groups:
        name = group.get("name")
        options = group.get("options", [])
        if not name or not isinstance(options, list) or len(options) == 0:
            continue
        groups.append({"name": name, "options": options})

    if not groups:
        return []

    variants: List[Dict[str, Any]] = []
    for index, combination in enumerate(
        product(*[group["options"] for group in groups])
    ):
        steps = [step for step in combination if isinstance(step, dict)]
        label_parts = [
            f"{group['name']}={step.get('label', step.get('type', 'option'))}"
            for group, step in zip(groups, combination)
        ]
        variants.append(
            {
                "id": f"feature_variant_{index}",
                "label": " + ".join(label_parts),
                "steps": steps,
            }
        )

    return variants
