"""欄位對齊功能給 Gemini 的 prompt 與 response schema。

跟論文分析的 prompt 分開放：兩者互不相干，混在同一個檔案裡調整
其中一邊的措辭很容易誤傷另一邊。
"""

MAX_CHAT_HISTORY = 10
MAX_CHAT_ACTIONS = 10

FIELD_MAPPING_SYSTEM_INSTRUCTION = """你是資料欄位對映助手。
使用者有一份資料表，另有一篇論文要求的變數清單，你的工作是判斷
每個「論文變數」對應到使用者資料表的哪一個欄位。

【絕對規則】
1. 只輸出 JSON 本體，不得包含 markdown、程式碼區塊或任何說明文字。
2. 欄位名稱只能從使用者提供的欄位清單中挑選，絕不可自行創造或改寫名稱。
3. 不確定時寧可回報 null 與候選清單，也不要勉強配對。
4. 只回報你被要求處理的項目，不要擅自更動其他項目。

【判斷依據】
- 語意同義：sex 與 gender、dob 與 date_of_birth、bp_sys 與 systolic_bp 是同一件事
- 醫療常見縮寫：pt = patient、adm = admission、dx = diagnosis、hr = heart rate、
  bp = blood pressure、wbc = white blood cell、los = length of stay
- 樣本值型態：論文變數需要數值，而該欄位的樣本值是文字時，
  即使名稱相似也要降低信心度
- 論文變數的型態與欄位樣本值明顯不符時，寧可回報 null"""


SEMANTIC_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paper_variable": {"type": "string"},
                    "matched_user_column": {"type": "string", "nullable": True},
                    "confidence_score": {"type": "number"},
                    "candidate_columns": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "paper_variable",
                    "matched_user_column",
                    "confidence_score",
                    "candidate_columns",
                ],
            },
        },
    },
    "required": ["matches"],
}


CHAT_REFINE_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paper_variable": {"type": "string"},
                    "matched_user_column": {"type": "string", "nullable": True},
                    "status": {
                        "type": "string",
                        "enum": ["AUTO_MATCHED", "NEEDS_REVIEW", "UNMATCHED"],
                    },
                    "confidence_score": {"type": "number"},
                },
                "required": [
                    "paper_variable",
                    "matched_user_column",
                    "status",
                    "confidence_score",
                ],
            },
        },
        "reply": {"type": "string"},
    },
    "required": ["actions", "reply"],
}


def _format_columns(user_columns: list[dict]) -> str:
    if not user_columns:
        return "（無欄位）"
    lines = []
    for column in user_columns:
        samples = column.get("sample_values") or []
        preview = ", ".join(str(value) for value in samples[:5]) if samples else "（無樣本值）"
        lines.append(f"- {column['name']}（樣本值：{preview}）")
    return "\n".join(lines)


def _format_pending(items: list[dict]) -> str:
    if not items:
        return "（無待配對項目）"
    lines = []
    for item in items:
        required_type = item.get("required_type") or "未指定"
        lines.append(f"- {item['paper_variable']}（需要型態：{required_type}）")
    return "\n".join(lines)


def _format_mapping_status(mapping_status: list[dict]) -> str:
    if not mapping_status:
        return "（無對映項目）"
    lines = []
    for item in mapping_status:
        matched = item.get("matched_user_column") or "（未對應）"
        lines.append(
            f"- {item['paper_variable']}"
            f"（型態：{item.get('required_type') or '未指定'}）"
            f" → {matched}　狀態：{item.get('status')}"
        )
    return "\n".join(lines)


def _format_history(chat_history: list) -> str:
    recent = (chat_history or [])[-MAX_CHAT_HISTORY:]
    if not recent:
        return "（尚無對話）"
    lines = []
    for message in recent:
        role = "使用者" if message.get("role") == "user" else "助理"
        lines.append(f"{role}：{message.get('content', '')}")
    return "\n".join(lines)


def build_semantic_match_prompt(items: list[dict], user_columns: list[dict]) -> str:
    """語意配對的請求 prompt（角色與規則已在 system_instruction 中）。"""
    return (
        "請為下列每一個論文變數，從使用者欄位清單中找出對應的欄位。\n\n"
        "【輸出規則】\n"
        "1. matched_user_column 只能是下方欄位清單中出現過的名稱，或 null。\n"
        "2. 不確定時 matched_user_column 填 null，並在 candidate_columns 列出 1~3 個可能欄位。\n"
        "3. 完全找不到合理對應時，matched_user_column 填 null、candidate_columns 填空陣列。\n"
        "4. confidence_score 是 0.0 到 1.0 的數值，代表你的把握程度。\n"
        "5. 每一個待配對的論文變數都必須有一筆輸出，不可遺漏。\n\n"
        "【使用者欄位清單】\n"
        f"{_format_columns(user_columns)}\n\n"
        "【待配對的論文變數】\n"
        f"{_format_pending(items)}\n\n"
        "【輸出格式】\n"
        '{"matches": [\n'
        '  {"paper_variable": "systolic_bp", "matched_user_column": "bp_sys",\n'
        '   "confidence_score": 0.85, "candidate_columns": []},\n'
        '  {"paper_variable": "braden_score", "matched_user_column": null,\n'
        '   "confidence_score": 0.0, "candidate_columns": ["braden_total"]}\n'
        "]}"
    )


def build_chat_refine_prompt(
    mapping_status: list[dict],
    user_columns: list[dict],
    chat_history: list,
    user_message: str,
) -> str:
    """對話式修正的請求 prompt。只要求輸出這一輪的變動，不要整包狀態。"""
    return (
        "使用者正在檢視論文變數與資料表欄位的對應關係，並用自然語言要求修改。\n"
        "請依使用者這次的訊息，輸出「這一輪要改變的項目」。\n\n"
        "【輸出規則】\n"
        "1. actions 只列出這一輪要改變的項目，不要輸出完整的對映清單。\n"
        "2. 使用者沒有提到的變數，一律不要放進 actions。\n"
        "3. matched_user_column 只能是下方欄位清單中出現過的名稱，"
        "或 null 表示解除對應。\n"
        "4. paper_variable 只能是下方「目前對映狀態」中已存在的變數名稱。\n"
        "5. 由你的建議所產生的對應，status 一律填 NEEDS_REVIEW，"
        "不可填 AUTO_MATCHED。\n"
        f"6. actions 最多 {MAX_CHAT_ACTIONS} 筆。若使用者的要求會影響更多項目，"
        "請不要輸出 actions，改在 reply 中請他說得更具體。\n"
        "7. reply 用繁體中文簡短說明你做了什麼。若有無法執行的要求"
        "（例如他指定的欄位不存在），必須在 reply 中說明原因。\n"
        "8. 使用者只是提問而沒有要求修改時，actions 填空陣列，只在 reply 中回答。\n\n"
        "【目前對映狀態】\n"
        f"{_format_mapping_status(mapping_status)}\n\n"
        "【使用者欄位清單】\n"
        f"{_format_columns(user_columns)}\n\n"
        "【對話記錄】\n"
        f"{_format_history(chat_history)}\n\n"
        "【使用者這次的訊息】\n"
        f"{user_message}\n\n"
        "【輸出格式】\n"
        "{\n"
        '  "actions": [\n'
        '    {"paper_variable": "braden_score", "matched_user_column": "braden_total",\n'
        '     "status": "NEEDS_REVIEW", "confidence_score": 0.9}\n'
        "  ],\n"
        '  "reply": "已把 braden_score 對應到 braden_total，請確認。"\n'
        "}"
    )
