from typing import Any, Dict, List
from xgboost import XGBClassifier
from .base import BaseModelWrapper

class XGBoostModel(BaseModelWrapper):
    name = "XGBoost"
    description = "Gradient boosting classifier with imbalance handling."

    def create_estimator(self) -> Any:
        return XGBClassifier(
            use_label_encoder=False, eval_metric="logloss", random_state=42
        )

    def get_param_grid(self) -> Dict[str, List[Any]]:
        return self.build_param_grid(
            {
                "n_estimators": [50, 150, 250],
                "max_depth": [3, 6, 10],
                "learning_rate": [0.01, 0.1, 0.2],
                "scale_pos_weight": [1, 5, 10],
            }
        )


