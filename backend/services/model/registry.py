from typing import Dict, List, Optional

from .models.base import BaseModelWrapper
from .defaults import (
    AdaBoostModel,
    BaggingModel,
    BalancedRandomForestModel,
    BernoulliNBModel,
    CalibratedClassifierModel,
    CatBoostModel,
    ComplementNBModel,
    DecisionTreeModel,
    EasyEnsembleModel,
    ExtraTreesModel,
    GaussianNBModel,
    GradientBoostingModel,
    HistGradientBoostingModel,
    KNNModel,
    LinearDiscriminantAnalysisModel,
    LightGBMModel,
    LogisticRegressionModel,
    MLPModel,
    MultinomialNBModel,
    QuadraticDiscriminantAnalysisModel,
    RadiusNeighborsModel,
    RidgeClassifierModel,
    SGDClassifierModel,
    PassiveAggressiveModel,
    RandomForestModel,
    SVMModel,
    XGBoostModel,
)


class ModelRegistry:
    """模型註冊中心：用來動態新增、查詢、列出所有模型配置。"""

    _registry: Dict[str, BaseModelWrapper] = {}

    @classmethod
    def register_model(cls, wrapper: BaseModelWrapper) -> None:
        cls._registry[wrapper.name] = wrapper

    @classmethod
    def unregister_model(cls, model_name: str) -> None:
        cls._registry.pop(model_name, None)

    @classmethod
    def get_model_config(cls, model_name: str) -> Optional[BaseModelWrapper]:
        return cls._registry.get(model_name)

    @classmethod
    def list_models(cls) -> List[str]:
        return list(cls._registry.keys())

    @classmethod
    def get_all_configs(cls) -> List[BaseModelWrapper]:
        return list(cls._registry.values())


def register_default_models() -> None:
    ModelRegistry.register_model(LogisticRegressionModel())
    ModelRegistry.register_model(KNNModel())
    ModelRegistry.register_model(SVMModel())
    ModelRegistry.register_model(DecisionTreeModel())
    ModelRegistry.register_model(RidgeClassifierModel())
    ModelRegistry.register_model(LinearDiscriminantAnalysisModel())
    ModelRegistry.register_model(QuadraticDiscriminantAnalysisModel())
    ModelRegistry.register_model(MLPModel())
    ModelRegistry.register_model(SGDClassifierModel())
    ModelRegistry.register_model(BaggingModel())
    ModelRegistry.register_model(RandomForestModel())
    ModelRegistry.register_model(ExtraTreesModel())
    ModelRegistry.register_model(GradientBoostingModel())
    ModelRegistry.register_model(HistGradientBoostingModel())
    ModelRegistry.register_model(AdaBoostModel())
    ModelRegistry.register_model(PassiveAggressiveModel())
    ModelRegistry.register_model(CalibratedClassifierModel())
    ModelRegistry.register_model(GaussianNBModel())
    ModelRegistry.register_model(MultinomialNBModel())
    ModelRegistry.register_model(ComplementNBModel())
    ModelRegistry.register_model(BernoulliNBModel())
    ModelRegistry.register_model(RadiusNeighborsModel())
    ModelRegistry.register_model(XGBoostModel())
    ModelRegistry.register_model(LightGBMModel())
    ModelRegistry.register_model(CatBoostModel())
    if BalancedRandomForestModel is not None:
        ModelRegistry.register_model(BalancedRandomForestModel())
    if EasyEnsembleModel is not None:
        ModelRegistry.register_model(EasyEnsembleModel())


def extract_model_components(
    payload: dict,
    model_names: Optional[List[str]] = None,
) -> List[Dict[str, Optional[str]]]:
    """從 AI JSON payload 中萃取需要的 model component。

    payload 範例為：
    {
      "features": [...],
      "models": [
        { "name": "Decision Tree (DT)", "type": "分類模型", "purpose": "..." },
        ...
      ]
    }

    如果提供 model_names，則只回傳名稱符合的模型元件。
    """
    models = payload.get("models") if isinstance(payload, dict) else []
    if not isinstance(models, list):
        return []

    result: List[Dict[str, Optional[str]]] = []
    for model in models:
        if not isinstance(model, dict):
            continue

        name = model.get("name")
        if model_names is not None and name not in model_names:
            continue

        result.append(
            {
                "name": name,
                "type": model.get("type"),
                "purpose": model.get("purpose"),
            }
        )

    return result


# Register models when module is imported.
register_default_models()
