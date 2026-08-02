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

# AI 語意建議的信心度上限：刻意壓在 AUTO_THRESHOLD 之下，
# 讓綠勾勾只保留給演算法層有把握的配對
SEMANTIC_SCORE_CAP = 0.79
_MAX_CANDIDATES = 5

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


def normalize_user_columns(user_columns: list) -> list[dict]:
    """把使用者欄位統一成 {"name": str, "sample_values": list[str]}。

    只給字串的呼叫端（沒帶樣本值）也接受，不報錯 —— 樣本值只是輔助訊號，
    沒有它配對照樣能跑，只是準確率會差一點。
    """
    normalized: list[dict] = []
    for column in user_columns or []:
        if isinstance(column, str):
            name, samples = column.strip(), []
        elif isinstance(column, dict):
            name = str(column.get("name", "")).strip()
            samples = [str(value) for value in (column.get("sample_values") or [])]
        else:
            continue
        if not name:
            continue
        normalized.append({"name": name, "sample_values": samples})
    return normalized


def _status_for(score: float) -> str:
    if score >= AUTO_THRESHOLD:
        return AUTO_MATCHED
    if score >= REVIEW_THRESHOLD:
        return NEEDS_REVIEW
    return UNMATCHED


def _score_candidates(name: str, required_type: str, columns: list[dict]) -> list[tuple[str, float]]:
    """算出這個論文變數對每個欄位的分數，由高到低排序。

    正規化後完全相同的欄位直接給 1.0 且不做型態加減分：名稱完全一致已經是
    夠強的證據，不該被樣本值推翻（例如欄位真的叫 age、但裡面資料很髒）。
    """
    column_names = [column["name"] for column in columns]
    samples = {column["name"]: column["sample_values"] for column in columns}
    exact = exact_match(name, column_names)

    scored = []
    for column_name, ratio in fuzzy_match(name, column_names):
        if column_name == exact:
            scored.append((column_name, 1.0))
        else:
            scored.append((
                column_name,
                boost_by_sample_values(ratio, required_type, samples[column_name]),
            ))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def run_auto_mapping(paper_variables: list[dict], user_columns: list[dict]) -> dict:
    """字串比對 + 樣本值輔助的自動對映，產出初始對映狀態。"""
    columns = normalize_user_columns(user_columns)
    samples_by_name = {column["name"]: column["sample_values"] for column in columns}

    variables: list[dict] = []
    for raw in paper_variables or []:
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        is_target = bool(raw.get("is_target", False))
        required_type = str(raw.get("type", "") or "")
        variables.append({
            "name": name,
            "type": required_type,
            "is_target": is_target,
            # target 一律視為必要，不管呼叫端傳什麼
            "required": True if is_target else bool(raw.get("required", True)),
            "candidates": _score_candidates(name, required_type, columns),
        })

    # target 先分配，確保它不會被其他變數搶走欄位；其餘依最佳分數由高到低
    order = sorted(
        variables,
        key=lambda item: (
            0 if item["is_target"] else 1,
            -(item["candidates"][0][1] if item["candidates"] else 0.0),
        ),
    )

    taken: set[str] = set()
    assignment: dict[str, tuple[str | None, float]] = {}
    for variable in order:
        chosen_name: str | None = None
        chosen_score = 0.0
        for column_name, score in variable["candidates"]:
            if score < REVIEW_THRESHOLD:
                break  # 已排序，後面只會更低
            if column_name in taken:
                continue
            chosen_name, chosen_score = column_name, score
            break
        if chosen_name is not None:
            taken.add(chosen_name)
        assignment[variable["name"]] = (chosen_name, chosen_score)

    mapping_status = []
    for variable in variables:  # 依輸入順序輸出，前端不需要再排
        matched, score = assignment[variable["name"]]
        if matched is None:
            status = UNMATCHED
            score = 0.0
        else:
            status = _status_for(score)
            if variable["is_target"] and status == AUTO_MATCHED:
                status = NEEDS_REVIEW  # target 一律人工確認
        mapping_status.append({
            "paper_variable": variable["name"],
            "required_type": variable["type"],
            "matched_user_column": matched,
            "confidence_score": round(score, 4),
            "status": status,
            "sample_values": samples_by_name.get(matched, []) if matched else [],
            "candidate_columns": (
                [name for name, _ in variable["candidates"][:3]]
                if status == UNMATCHED
                else []
            ),
        })

    return {
        "total_required": sum(1 for variable in variables if variable["required"]),
        "matched_count": sum(1 for item in mapping_status if item["status"] == AUTO_MATCHED),
        "mapping_status": mapping_status,
    }


def merge_semantic_suggestions(
    result: dict,
    suggestions: list[dict],
    user_columns: list[dict],
) -> dict:
    """把 Gemini 的語意建議併回 run_auto_mapping() 的結果（原地修改並回傳）。

    只影響非 AUTO_MATCHED 的項目：演算法層已經有把握的配對不容 AI 推翻。
    AI 建議產生的配對一律標成 NEEDS_REVIEW、信心度上限 SEMANTIC_SCORE_CAP，
    確保使用者一定會親眼確認過。
    """
    samples_by_name = {column["name"]: column["sample_values"] for column in user_columns}
    by_variable = {item["paper_variable"]: item for item in result["mapping_status"]}
    taken = {
        item["matched_user_column"]
        for item in result["mapping_status"]
        if item["matched_user_column"]
    }

    for suggestion in suggestions or []:
        item = by_variable.get(suggestion.get("paper_variable"))
        if item is None or item["status"] == AUTO_MATCHED:
            continue

        column = suggestion.get("matched_user_column")
        extra = list(suggestion.get("candidate_columns") or [])

        if column and column not in taken:
            item["matched_user_column"] = column
            item["confidence_score"] = min(
                float(suggestion.get("confidence_score") or 0.0),
                SEMANTIC_SCORE_CAP,
            )
            item["status"] = NEEDS_REVIEW
            item["sample_values"] = samples_by_name.get(column, [])
            item["candidate_columns"] = []
            taken.add(column)
            continue

        if column:
            extra.append(column)  # 欄位已被佔用 → 降格為候選，讓使用者自己決定要不要搶
        merged = list(item["candidate_columns"])
        for name in extra:
            if name not in merged:
                merged.append(name)
        item["candidate_columns"] = merged[:_MAX_CANDIDATES]

    result["matched_count"] = sum(
        1 for item in result["mapping_status"] if item["status"] == AUTO_MATCHED
    )
    return result
