"""strategy="auto" 讓同一個 fill_na 步驟依欄位型別分流：
數值型欄位補平均值、名目/類別型欄位補眾數 —— 不用手動拆成兩個步驟、
也不用自己先分好 columns 清單。
"""

import pandas as pd

from services.workflow.preprocess_service import _fill_na_fit


def test_fill_na_fit_auto_strategy_uses_mean_for_numeric_and_mode_for_categorical():
    train = pd.DataFrame({
        "age": [20, 30, None, 40],
        "gender": ["M", "F", "F", None],
    })

    state = _fill_na_fit(train, {"type": "fill_na", "strategy": "auto"})

    assert state["fill_values"]["age"] == 30.0  # mean of 20, 30, 40
    assert state["fill_values"]["gender"] == "F"  # mode of M, F, F
