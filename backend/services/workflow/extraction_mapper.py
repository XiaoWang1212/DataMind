from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from services.model.registry import ModelRegistry

MODEL_ALIASES = {
    "supportvectormachine": "SVM",
    "supportvectormachinesvc": "SVM",
    "svc": "SVM",
    "randomforest": "Random Forest",
    "rf": "Random Forest",
    "decisiontree": "Decision Tree",
    "logisticregression": "Logistic Regression",
    "gradientboosting": "Gradient Boosting",
    "histgradientboosting": "HistGradientBoosting",
    "adaboost": "AdaBoost",
    "bagging": "Bagging",
    "extratrees": "Extra Trees",
    "mlp": "MLP",
    "sgdclassifier": "SGD Classifier",
    "sgd": "SGD Classifier",
    "gaussiannb": "Gaussian NB",
    "multinomialnb": "Multinomial NB",
    "complementnb": "Complement NB",
    "bernoullinb": "Bernoulli NB",
    "radiusneighbors": "Radius Neighbors",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
    "balancedrandomforest": "Balanced Random Forest",
    "easyensemble": "Easy Ensemble",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower().strip())


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def normalize_model_name(model_name: Optional[str]) -> Optional[str]:
    if not model_name:
        return None

    candidate = _normalize_text(str(model_name))
    registered = ModelRegistry.list_models()

    for name in registered:
        if _normalize_text(name) == candidate:
            return name

    if candidate in MODEL_ALIASES:
        alias = MODEL_ALIASES[candidate]
        if ModelRegistry.get_model_config(alias) is not None:
            return alias

    for alias, canonical in MODEL_ALIASES.items():
        if alias in candidate or candidate in alias:
            if ModelRegistry.get_model_config(canonical) is not None:
                return canonical

    for name in registered:
        normalized_name = _normalize_text(name)
        if normalized_name in candidate or candidate in normalized_name:
            return name

    return str(model_name)


def parse_model_names(models: Any) -> List[str]:
    if models is None:
        return []

    if isinstance(models, str):
        try:
            models = json.loads(models)
        except json.JSONDecodeError:
            return [models]

    if isinstance(models, dict):
        models = [models]

    if not isinstance(models, list):
        return []

    result: List[str] = []
    for item in models:
        if isinstance(item, str):
            normalized = normalize_model_name(item)
            if normalized:
                result.append(normalized)
        elif isinstance(item, dict):
            name = item.get("name") or item.get("model") or item.get("type")
            if name:
                normalized = normalize_model_name(name)
                if normalized:
                    result.append(normalized)
    return result


def parse_steps(steps: Any) -> List[Dict[str, Any]]:
    value = _parse_json_field(steps)
    if isinstance(value, dict):
        # single step object is wrapped as one pipeline
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def parse_step_pipelines(raw: Any) -> List[List[Dict[str, Any]]]:
    parsed = _parse_json_field(raw)
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return [parse_steps(parsed)]
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], list):
        return [
            [step for step in pipeline if isinstance(step, dict)] for pipeline in parsed
        ]
    return []


def parse_validation_config(raw: Any) -> Dict[str, Any]:
    validation = _parse_json_field(raw)
    if isinstance(validation, str):
        return {"method": validation}
    if isinstance(validation, dict):
        return validation
    return {}


def parse_score_variants(raw: Any) -> List[Dict[str, Any]]:
    metrics = _parse_json_field(raw)
    if isinstance(metrics, dict):
        metrics = [metrics]
    if not isinstance(metrics, list):
        return []

    variants: List[Dict[str, Any]] = []
    for item in metrics:
        if isinstance(item, str):
            variants.append({"metric": item})
            continue
        if isinstance(item, dict):
            metric = item.get("metric") or item.get("name") or item.get("type")
            if not metric:
                continue
            variant = {
                "metric": metric,
            }
            for key in ["threshold", "pos_label", "labels", "id"]:
                if key in item:
                    variant[key] = item[key]
            variants.append(variant)
    return variants


def build_workflow_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    preprocess_pipelines = parse_step_pipelines(
        payload.get("preprocessing") or payload.get("preprocess")
    )
    feature_engineering_pipelines = parse_step_pipelines(
        payload.get("featureEngineering") or payload.get("feature_engineering")
    )
    model_names = parse_model_names(payload.get("models") or payload.get("model_names"))
    validation_config = parse_validation_config(
        payload.get("validation") or payload.get("validation_config")
    )
    score_variants = parse_score_variants(
        payload.get("metrics") or payload.get("score_variants")
    )
    target_col = (
        payload.get("target_col")
        or payload.get("targetCol")
        or payload.get("target")
        or None
    )

    return {
        "preprocess_pipelines": preprocess_pipelines,
        "feature_engineering_pipelines": feature_engineering_pipelines,
        "model_names": model_names,
        "validation_config": validation_config,
        "score_variants": score_variants,
        "target_col": target_col,
    }
