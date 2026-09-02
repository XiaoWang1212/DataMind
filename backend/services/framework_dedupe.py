"""框架重複比對用的正規化工具

判定依據是 PDF 內容的 SHA-256；hash 比不到時退而比檔名。
兩種比對都要先把值收斂成同一種寫法再比。
"""

import re

_NOISE = re.compile(r"[\s_\-]+")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def normalize_title(value) -> str:
    """正規化標題或檔名，讓大小寫與空白/底線的差異不影響比對"""
    return _NOISE.sub("", str(value or "").strip().lower())


def normalize_hash(value) -> str:
    """正規化 SHA-256；格式不符時回傳空字串，呼叫端應視為沒有 hash

    長度與字元檢查是為了讓壞掉的輸入落成空字串，而不是拿垃圾值去比對——
    否則兩筆同樣壞掉的值會被判成重複。
    """
    normalized = str(value or "").strip().lower()
    return normalized if _HEX_64.match(normalized) else ""
