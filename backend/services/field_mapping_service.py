"""欄位對齊：把論文擷取出的變數對映到使用者資料表的欄位。

純函式模組，不依賴 Flask 也不依賴 Gemini，可以獨立測試。
Gemini 的語意補強在 services/gemini_service.py，合併規則在本檔的
merge_semantic_suggestions()。
"""

import re
from difflib import SequenceMatcher

AUTO_MATCHED = "AUTO_MATCHED"
NEEDS_REVIEW = "NEEDS_REVIEW"
UNMATCHED = "UNMATCHED"

# 門檻集中在這裡：真實資料驗證後若假陽性偏高，只調這幾個數字
AUTO_THRESHOLD = 0.8
REVIEW_THRESHOLD = 0.5

# 前綴要有分隔符號才算前綴，避免把 "tblname" 這種名字誤剝成 "name"
_PREFIX_RE = re.compile(r"^(?:tbl|col)[\s_-]+", re.IGNORECASE)
_SEPARATOR_RE = re.compile(r"[\s_-]+")


def normalize_field(name: str) -> str:
    """欄位名正規化：轉小寫 → 去 tbl_/col_ 前綴 → 去空白/底線/破折號。

    去前綴必須在去分隔符號之前，否則 "tbl_user_name" 會先被壓成
    "tblusername"，前綴就認不出來了。
    """
    if not name:
        return ""
    result = _PREFIX_RE.sub("", name.strip().lower())
    return _SEPARATOR_RE.sub("", result)


def exact_match(paper_var: str, user_columns: list[str]) -> str | None:
    """正規化後完全相同的第一個欄位，回傳原始欄位名；沒有則 None。"""
    target = normalize_field(paper_var)
    if not target:
        return None
    for column in user_columns:
        if normalize_field(column) == target:
            return column
    return None


def fuzzy_match(paper_var: str, user_columns: list[str]) -> list[tuple[str, float]]:
    """對每個欄位算字串相似度，依分數由高到低排序回傳。

    分數相同時維持輸入順序（Python 的 sort 是穩定排序），確保結果可重現。
    """
    target = normalize_field(paper_var)
    scored = [
        (column, SequenceMatcher(None, target, normalize_field(column)).ratio())
        for column in user_columns
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
