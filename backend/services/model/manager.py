from .models.base import BaseModelWrapper
from .registry import ModelRegistry, register_default_models
from .defaults import LogisticRegressionModel, RandomForestModel
from .evaluator import AutomationModelEvaluator, ModelResult

try:
    from .defaults import XGBoostModel
except ImportError:  # pragma: no cover
    XGBoostModel = None


register_default_models()

__all__ = [
    "BaseModelWrapper",
    "ModelRegistry",
    "register_default_models",
    "LogisticRegressionModel",
    "RandomForestModel",
    "XGBoostModel",
    "AutomationModelEvaluator",
    "ModelResult",
]


if __name__ == "__main__":
    import numpy as np

    print("🚀 Model Manager Demo")
    np.random.seed(42)
    X = np.random.randn(120, 20)
    y = np.random.randint(0, 2, size=120)

    evaluator = AutomationModelEvaluator(outer_cv=5, inner_cv=3)
    result_df = evaluator.compare_models(X, y)
    print(result_df.to_string(index=False))
