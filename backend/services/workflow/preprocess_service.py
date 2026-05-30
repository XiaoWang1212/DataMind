from __future__ import annotations

from itertools import product
from typing import Any, Dict, List

import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

PREPROCESS_STEP_TYPES = {
    "drop_columns",
    "fill_na",
    "normalize",
    "standardize",
    "one_hot",
    "label_encode",
}


def _fill_na(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    strategy = step.get("strategy", "constant")
    value = step.get("value", 0)

    if not columns:
        return df.fillna(value)

    for column in columns:
        if column not in df.columns:
            continue
        if strategy == "mean":
            df[column] = df[column].fillna(df[column].mean())
        elif strategy == "median":
            df[column] = df[column].fillna(df[column].median())
        else:
            df[column] = df[column].fillna(value)

    return df


def _drop_columns(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns", [])
    if not columns:
        return df
    return df.drop(
        columns=[col for col in columns if col in df.columns], errors="ignore"
    )


def _normalize(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    numeric = df.select_dtypes(include=["number"]).columns.tolist()
    target_columns = [col for col in (columns or numeric) if col in df.columns]
    if not target_columns:
        return df

    scaler = MinMaxScaler()
    df[target_columns] = scaler.fit_transform(df[target_columns])
    return df


def _standardize(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    numeric = df.select_dtypes(include=["number"]).columns.tolist()
    target_columns = [col for col in (columns or numeric) if col in df.columns]
    if not target_columns:
        return df

    scaler = StandardScaler()
    df[target_columns] = scaler.fit_transform(df[target_columns])
    return df


def _one_hot(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    if not columns:
        columns = df.select_dtypes(include=["object", "category"]).columns.tolist()
    columns = [col for col in columns if col in df.columns]
    if not columns:
        return df

    return pd.get_dummies(df, columns=columns, drop_first=False)


def _label_encode(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    if not columns:
        columns = df.select_dtypes(include=["object", "category"]).columns.tolist()

    for column in columns:
        if column not in df.columns:
            continue
        if df[column].dtype.name == "category" or df[column].dtype == object:
            encoder = LabelEncoder()
            df[column] = encoder.fit_transform(df[column].astype(str))

    return df


def apply_preprocess_pipeline(
    df: pd.DataFrame,
    pipeline_steps: List[Dict[str, Any]],
) -> pd.DataFrame:
    result = df.copy()

    for step in pipeline_steps:
        step_type = step.get("type")
        if step_type not in PREPROCESS_STEP_TYPES:
            continue

        if step_type == "drop_columns":
            result = _drop_columns(result, step)
        elif step_type == "fill_na":
            result = _fill_na(result, step)
        elif step_type == "normalize":
            result = _normalize(result, step)
        elif step_type == "standardize":
            result = _standardize(result, step)
        elif step_type == "one_hot":
            result = _one_hot(result, step)
        elif step_type == "label_encode":
            result = _label_encode(result, step)

    return result


def generate_preprocess_variants(
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
                "id": f"preprocess_variant_{index}",
                "label": " + ".join(label_parts),
                "steps": steps,
            }
        )

    return variants
