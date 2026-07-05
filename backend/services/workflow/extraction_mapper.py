from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from services.model.registry import ModelRegistry

MODEL_ALIASES = {
    # SVM variants
    "supportvectormachine": "SVM",
    "supportvectormachinesvc": "SVM",
    "svc": "SVM",
    "svmclassifier": "SVM",
    "linearsvc": "Linear SVC",
    "linearsupportvectormachine": "Linear SVC",
    "nusvc": "Nu-SVC",
    "nusupportvectormachine": "Nu-SVC",
    "nusvm": "Nu-SVC",
    # Tree & ensemble
    "randomforest": "Random Forest",
    "randomforestclassifier": "Random Forest",
    "rf": "Random Forest",
    "decisiontree": "Decision Tree",
    "decisiontreeclassifier": "Decision Tree",
    "dt": "Decision Tree",
    "extratrees": "Extra Trees",
    "extratreesclassifier": "Extra Trees",
    "et": "Extra Trees",
    "gradientboosting": "Gradient Boosting",
    "gradientboostingclassifier": "Gradient Boosting",
    "gbm": "Gradient Boosting",
    "histgradientboosting": "HistGradient Boosting",
    "histgradientboostingclassifier": "HistGradient Boosting",
    "hgbc": "HistGradient Boosting",
    "adaboost": "AdaBoost",
    "adaboostclassifier": "AdaBoost",
    "bagging": "Bagging",
    "baggingclassifier": "Bagging",
    # Ensemble meta
    "votingclassifier": "Voting Classifier",
    "voting": "Voting Classifier",
    "softvoter": "Voting Classifier",
    "stackingclassifier": "Stacking Classifier",
    "stacking": "Stacking Classifier",
    "stackedgeneralization": "Stacking Classifier",
    # Linear
    "logisticregression": "Logistic Regression",
    "lr": "Logistic Regression",
    "logit": "Logistic Regression",
    "logisticregressioncv": "Logistic Regression CV",
    "lrcv": "Logistic Regression CV",
    "ridgeclassifier": "Ridge Classifier",
    "ridge": "Ridge Classifier",
    "ridgeclassifiercv": "Ridge Classifier CV",
    "ridgecv": "Ridge Classifier CV",
    "sgdclassifier": "SGD Classifier",
    "sgd": "SGD Classifier",
    "passiveaggressive": "Passive Aggressive",
    "passiveaggressiveclassifier": "Passive Aggressive",
    # Neighbors
    "kneighbors": "K-Nearest Neighbors",
    "knn": "K-Nearest Neighbors",
    "knearestneighbors": "K-Nearest Neighbors",
    "kneighborsclassifier": "K-Nearest Neighbors",
    "radiusneighbors": "Radius Neighbors",
    "radiusneighborsclassifier": "Radius Neighbors",
    # Discriminant
    "lda": "Linear Discriminant Analysis",
    "lineardiscriminantanalysis": "Linear Discriminant Analysis",
    "qda": "Quadratic Discriminant Analysis",
    "quadraticdiscriminantanalysis": "Quadratic Discriminant Analysis",
    # Neural net
    "mlp": "MLP",
    "mlpclassifier": "MLP",
    "multilayerperceptron": "MLP",
    "neuralnetwork": "MLP",
    # Naive Bayes
    "gaussiannb": "Gaussian NB",
    "gnb": "Gaussian NB",
    "multinomialnb": "Multinomial NB",
    "complementnb": "Complement NB",
    "bernoullinb": "Bernoulli NB",
    # Gaussian Process
    "gaussianprocess": "Gaussian Process",
    "gaussianprocessclassifier": "Gaussian Process",
    "gpc": "Gaussian Process",
    # Calibrated
    "calibratedclassifier": "Calibrated Classifier",
    "calibratedclassifiercv": "Calibrated Classifier",
    # Third-party boosting
    "xgboost": "XGBoost",
    "xgb": "XGBoost",
    "lightgbm": "LightGBM",
    "lgbm": "LightGBM",
    "catboost": "CatBoost",
    # Imbalanced
    "balancedrandomforest": "Balanced Random Forest",
    "brf": "Balanced Random Forest",
    "easyensemble": "Easy Ensemble",
    "eec": "Easy Ensemble",
}

# Canonical resampling method names (what the backend accepts)
RESAMPLING_ALIASES = {
    "smote": "smote",
    "syntheticminorityoversampling": "smote",
    "adasyn": "adasyn",
    "adaptivesynthetic": "adasyn",
    "borderlinesmote": "borderline_smote",
    "randomoversampling": "random_oversample",
    "randomoversample": "random_oversample",
    "oversample": "random_oversample",
    "randomundersampling": "random_undersample",
    "randomundersample": "random_undersample",
    "undersample": "random_undersample",
    "smoteenn": "smoteenn",
    "smotetomek": "smotetomek",
    "none": "none",
    "no": "none",
}

TUNING_ALIASES = {
    "grid": "grid",
    "gridsearch": "grid",
    "gridsearchcv": "grid",
    "random": "random",
    "randomsearch": "random",
    "randomizedsearch": "random",
    "randomizedsearchcv": "random",
    "none": "none",
    "no": "none",
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


def normalize_resampling_method(raw: Any) -> str:
    if not raw:
        return "none"
    candidate = _normalize_text(str(raw))
    return RESAMPLING_ALIASES.get(candidate, "none")


def normalize_tuning_method(raw: Any) -> str:
    if not raw:
        return "none"
    candidate = _normalize_text(str(raw))
    return TUNING_ALIASES.get(candidate, "none")


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
            variant: Dict[str, Any] = {"metric": metric}
            for key in ["threshold", "pos_label", "labels", "id"]:
                if key in item:
                    variant[key] = item[key]
            variants.append(variant)
    return variants


def parse_resampling(raw: Any) -> Dict[str, Any]:
    """Parse resampling config from JSON payload.

    Accepts:
      "smote"
      { "method": "smote", "config": { "k_neighbors": 5 } }
      { "method": "smote", "k_neighbors": 5 }
    """
    value = _parse_json_field(raw)
    if value is None:
        return {"method": "none", "config": {}}
    if isinstance(value, str):
        return {"method": normalize_resampling_method(value), "config": {}}
    if isinstance(value, dict):
        method = normalize_resampling_method(
            value.get("method") or value.get("strategy") or value.get("type")
        )
        inner = value.get("config") or {}
        # allow flat keys like k_neighbors directly in the dict
        for k in ["k_neighbors", "n_neighbors", "sampling_strategy", "random_state", "kind"]:
            if k in value and k not in inner:
                inner[k] = value[k]
        return {"method": method, "config": inner if isinstance(inner, dict) else {}}
    return {"method": "none", "config": {}}


def parse_tuning(raw: Any) -> Dict[str, Any]:
    """Parse hyperparameter tuning config from JSON payload."""
    value = _parse_json_field(raw)
    defaults = {"method": "none", "cv": 3, "n_iter": 20, "scoring": "roc_auc"}
    if value is None:
        return defaults
    if isinstance(value, str):
        return {**defaults, "method": normalize_tuning_method(value)}
    if isinstance(value, dict):
        method = normalize_tuning_method(
            value.get("method") or value.get("strategy") or value.get("search")
        )
        return {
            "method": method,
            "cv": int(value.get("cv", 3)),
            "n_iter": int(value.get("n_iter", 20)),
            "scoring": str(value.get("scoring", "roc_auc")),
        }
    return defaults


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

    column_config = _parse_json_field(
        payload.get("column_config") or payload.get("columnConfig")
    )
    if isinstance(column_config, list):
        column_config = [item for item in column_config if isinstance(item, dict)]
    else:
        column_config = []

    resampling = parse_resampling(
        payload.get("resampling") or payload.get("resampling_method")
    )
    tuning = parse_tuning(
        payload.get("tuning") or payload.get("hyperparameter_tuning")
    )
    compute_ci = bool(payload.get("compute_ci", False))
    ci_n_bootstrap = int(payload.get("ci_n_bootstrap", 1000))

    return {
        "preprocess_pipelines": preprocess_pipelines,
        "feature_engineering_pipelines": feature_engineering_pipelines,
        "model_names": model_names,
        "validation_config": validation_config,
        "score_variants": score_variants,
        "target_col": target_col,
        "column_config": column_config,
        "resampling_method": resampling["method"],
        "resampling_config": resampling["config"],
        "tuning_method": tuning["method"],
        "tuning_cv": tuning["cv"],
        "tuning_n_iter": tuning["n_iter"],
        "tuning_scoring": tuning["scoring"],
        "compute_ci": compute_ci,
        "ci_n_bootstrap": ci_n_bootstrap,
    }
