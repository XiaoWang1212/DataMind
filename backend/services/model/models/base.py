from abc import ABC, abstractmethod
from inspect import signature
from typing import Any, Dict, List, Optional


class BaseModelWrapper(ABC):
    """抽象模型 wrapper：所有機器學習模型都應該繼承此 class。"""

    name: str
    description: Optional[str]

    @abstractmethod
    def create_estimator(self) -> Any:
        raise NotImplementedError

    def get_available_parameters(self) -> List[str]:
        estimator = self.create_estimator()
        params = signature(estimator.__init__).parameters
        return [
            name for name in params.keys() if name not in {"self", "args", "kwargs"}
        ]

    def _default_grid_for_param(self, param_name: str) -> List[Any]:
        if param_name in {"penalty"}:
            return ["l1", "l2", "elasticnet", "none"]
        if param_name in {"solver"}:
            return ["liblinear", "saga", "lbfgs", "newton-cg", "sag"]
        if param_name in {"class_weight"}:
            return ["balanced", None]
        if param_name in {"max_iter", "n_estimators", "epochs"}:
            return [100, 200, 500, 1000, 2000]
        if param_name in {
            "C",
            "alpha",
            "tol",
            "learning_rate",
            "gamma",
            "min_child_weight",
            "reg_alpha",
            "reg_lambda",
        }:
            return [0.0001, 0.001, 0.01, 0.1, 1.0]
        if param_name in {
            "l1_ratio",
            "subsample",
            "colsample_bytree",
            "colsample_bylevel",
            "colsample_bynode",
        }:
            return [0.0, 0.15, 0.5, 0.75, 1.0]
        if param_name in {
            "max_depth",
            "min_samples_leaf",
            "n_neighbors",
            "max_leaf_nodes",
        }:
            return [1, 3, 5, 10, None]
        if param_name in {
            "weights",
            "kernel",
            "activation",
            "method",
            "criterion",
            "splitter",
            "objective",
        }:
            return [
                "uniform",
                "distance",
                "linear",
                "rbf",
                "relu",
                "tanh",
                "sigmoid",
                "isotonic",
                "gini",
                "entropy",
                "log_loss",
                "best",
                "random",
                "binary:logistic",
            ]
        if param_name in {
            "fit_intercept",
            "dual",
            "shuffle",
            "early_stopping",
            "warm_start",
            "bootstrap",
        }:
            return [True, False]
        if param_name in {"radius"}:
            return [0.5, 1.0, 2.0]
        if param_name in {"n_jobs"}:
            return [-1, 1]
        return []

    def get_all_param_grid(self) -> Dict[str, List[Any]]:
        """Return a complete grid for all estimator parameters with default candidate values."""
        return self.build_param_grid()

    def build_param_grid(
        self, overrides: Optional[Dict[str, List[Any]]] = None
    ) -> Dict[str, List[Any]]:
        overrides = overrides or {}
        grid: Dict[str, List[Any]] = {}
        for key in self.get_available_parameters():
            if key in overrides:
                grid[key] = overrides[key]
                continue
            default_values = self._default_grid_for_param(key)
            if default_values:
                grid[key] = default_values
        return grid

    @abstractmethod
    def get_param_grid(self) -> Dict[str, List[Any]]:
        raise NotImplementedError
