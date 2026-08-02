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


_TYPE_BONUS = 0.1
_TYPE_PENALTY = 0.2

# 非空樣本值中至少要有這個比例符合，才算是該型態
_TYPE_MAJORITY = 0.6

_DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"),
    re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"),
    re.compile(r"^\d{8}$"),
)

# 論文變數的 type 字串 → 推斷型態。不在表內的一律視為無法判斷。
_TYPE_ALIASES = {
    "date": "date",
    "datetime": "date",
    "numerical": "numeric",
    "numeric": "numeric",
    "int": "numeric",
    "integer": "numeric",
    "float": "numeric",
    "continuous": "numeric",
    "categorical": "text",
    "category": "text",
    "string": "text",
    "text": "text",
    "nominal": "text",
}


def _is_numeric(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def infer_value_type(sample_values: list[str]) -> str | None:
    """從樣本值推斷欄位型態，無法判斷時回傳 None。

    日期先於數字判斷：YYYYMMDD 這種寫法同時符合兩者，但它是日期。
    """
    values = [str(value).strip() for value in sample_values or [] if str(value).strip()]
    if not values:
        return None

    threshold = len(values) * _TYPE_MAJORITY
    date_hits = sum(1 for value in values if any(p.match(value) for p in _DATE_PATTERNS))
    if date_hits >= threshold:
        return "date"

    numeric_hits = sum(1 for value in values if _is_numeric(value))
    if numeric_hits >= threshold:
        return "numeric"

    return "text"


def boost_by_sample_values(
    score: float,
    required_type: str,
    sample_values: list[str],
) -> float:
    """用樣本值的型態調整信心度。

    型態相符 +0.1、不符 -0.2、無法判斷不調整，結果 clamp 在 [0, 1]。
    不對稱是刻意的：型態不符是「這大概配錯了」的強訊號，
    型態相符只是「沒有反證」的弱訊號。
    """
    inferred = infer_value_type(sample_values)
    if inferred is None:
        return score

    expected = _TYPE_ALIASES.get((required_type or "").strip().lower())
    if expected is None:
        return score

    adjusted = score + _TYPE_BONUS if expected == inferred else score - _TYPE_PENALTY
    return max(0.0, min(1.0, adjusted))
