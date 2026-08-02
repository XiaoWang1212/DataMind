"""欄位對齊真實資料驗證腳本（Task 15）。

用法（在 backend/ 目錄下）：
    uv run python scripts/test_field_mapping.py <workflow_json> <dataset_file> [answer_json]

- <workflow_json>：論文分析得到的 workflow JSON。接受兩種形狀：
    1. 裸的 workflow dict（頂層就有 target_col / features）
    2. 包了一層的 {"result": {"workflow_json": {...}}}（/api/gemini/ai-analyze
       存檔的形狀，routes/gemini.py 的 _save_result() 就是這樣包的）
- <dataset_file>：真實資料表，依副檔名判斷讀法：
    - .csv：先試 utf-8-sig，失敗再試 big5（常見於院內舊系統匯出的檔案）
    - .xlsx：用 openpyxl 讀取，取第一個工作表
  只取前 5 筆非表頭資料列當樣本值，跟 run_auto_mapping() 用途一致。
- [answer_json]：**選填**。人工寫的正確答案 {"論文變數名": "應該對到的欄位名或 null"}。
  沒有給的話，只印對映表與各狀態數量，準確率與假陽性數會跳過並提示「需要人工答案卷」——
  真實醫療資料的答案卷不可用腳本捏造，捏造出來的準確率沒有意義。

量測的東西：
  1. 演算法層自動配對後，各狀態（AUTO_MATCHED / NEEDS_REVIEW / UNMATCHED）的數量
  2. Gemini semantic_match() 連續呼叫 5 次的 JSON 穩定性（None = 失敗，[] 或非空list = 成功）
  3.（有答案卷才有）自動配對正確率與假陽性清單
  4. target 變數是否有出現、狀態是否正確（target 不該被自動配對，需人工確認）
"""

import csv
import json
import sys
from io import StringIO
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

# 獨立腳本不會經過 app factory 的初始化流程，GEMINI_API_KEY 要自己從
# backend/.env 載入，否則 GeminiService() 會直接丟 ValueError。
load_dotenv(BACKEND_DIR / ".env")

from services.field_mapping_service import (  # noqa: E402
    AUTO_MATCHED,
    NEEDS_REVIEW,
    UNMATCHED,
    merge_semantic_suggestions,
    normalize_user_columns,
    run_auto_mapping,
)
from services.gemini_service import GeminiService  # noqa: E402

GEMINI_ROUNDS = 5
SAMPLE_ROWS = 5


def load_paper_variables(workflow_path: Path) -> tuple[list[dict], str]:
    """讀取論文變數清單。回傳 (variables, target_col)。

    workflow JSON 若沒有把 target_col 放進 features[]（常見情況——target 通常
    是研究結果而不是自變數），額外補一筆 is_target=True 的變數，確保
    run_auto_mapping() 一定會處理到 target。
    """
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow = data.get("result", {}).get("workflow_json", data)
    target_col = workflow.get("target_col") or ""
    variables = [
        {
            "name": feature["name"],
            "type": feature.get("type", ""),
            "is_target": feature["name"] == target_col,
        }
        for feature in workflow.get("features", [])
    ]
    if target_col and not any(v["name"] == target_col for v in variables):
        variables.insert(0, {"name": target_col, "type": "categorical", "is_target": True})
    return variables, target_col


def _read_csv_rows(csv_path: Path) -> tuple[list[str], list[list[str]]]:
    """先試 utf-8-sig，失敗再試 big5（院內舊系統常見編碼）。"""
    raw_bytes = csv_path.read_bytes()
    for encoding in ("utf-8-sig", "big5"):
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        reader = csv.reader(StringIO(text))
        rows = list(reader)
        if not rows:
            continue
        return rows[0], rows[1:]
    raise ValueError(f"{csv_path} 無法用 utf-8-sig 或 big5 解碼")


def _read_xlsx_rows(xlsx_path: Path) -> tuple[list[str], list[list]]:
    import openpyxl

    workbook = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    header = list(next(rows_iter))
    data_rows = [list(row) for row in rows_iter]
    return header, data_rows


def load_user_columns(dataset_path: Path, sample_rows: int = SAMPLE_ROWS) -> list[dict]:
    """讀取資料表欄位名 + 每欄前 N 筆樣本值，依副檔名判斷讀法（.csv 或 .xlsx）。"""
    suffix = dataset_path.suffix.lower()
    if suffix == ".xlsx":
        header, data_rows = _read_xlsx_rows(dataset_path)
    elif suffix == ".csv":
        header, data_rows = _read_csv_rows(dataset_path)
    else:
        raise ValueError(f"不支援的副檔名：{suffix}（只吃 .csv 或 .xlsx）")

    rows = data_rows[:sample_rows]
    columns = []
    for index, name in enumerate(header):
        name = "" if name is None else str(name)
        samples = []
        for row in rows:
            if index < len(row) and row[index] is not None and str(row[index]).strip() != "":
                samples.append(str(row[index]))
        columns.append({"name": name, "sample_values": samples})
    return normalize_user_columns(columns)


def _format_row(item: dict) -> str:
    matched = item["matched_user_column"] or "（無）"
    return (
        f"  {item['paper_variable']:<28} -> {matched:<20} "
        f"信心度={item['confidence_score']:.2f}  狀態={item['status']}"
    )


def print_mapping_table(mapping_status: list[dict]) -> None:
    print("\n[對映表] 論文變數 -> 對映欄位")
    for item in mapping_status:
        print(_format_row(item))


def print_status_counts(mapping_status: list[dict]) -> None:
    counts = {AUTO_MATCHED: 0, NEEDS_REVIEW: 0, UNMATCHED: 0}
    for item in mapping_status:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print("\n[狀態統計]")
    for status in (AUTO_MATCHED, NEEDS_REVIEW, UNMATCHED):
        print(f"  {status}: {counts[status]}")


def print_target_status(mapping_status: list[dict], target_col: str) -> None:
    print("\n[Target 檢查]")
    if not target_col:
        print("  workflow JSON 沒有 target_col，略過檢查")
        return
    target_item = next(
        (item for item in mapping_status if item["paper_variable"] == target_col), None
    )
    if target_item is None:
        print(f"  target_col={target_col!r} 沒有出現在對映表中")
        return
    print(
        f"  target_col={target_col!r} 出現，"
        f"對映到 {target_item['matched_user_column']!r}，狀態={target_item['status']}"
    )


def score_accuracy(mapping_status: list[dict], answers: dict) -> None:
    auto_items = [item for item in mapping_status if item["status"] == AUTO_MATCHED]
    correct = 0
    false_positives = []
    for item in auto_items:
        expected = answers.get(item["paper_variable"])
        if item["matched_user_column"] == expected:
            correct += 1
        else:
            false_positives.append(
                f"{item['paper_variable']}：配到 {item['matched_user_column']}，"
                f"正確答案是 {expected!r}"
            )

    accuracy = correct / len(auto_items) if auto_items else 0.0
    print("\n[準確率]（依人工答案卷計算）")
    print(f"  自動配對正確率：{correct}/{len(auto_items)} = {accuracy:.1%}")
    print(f"  假陽性：{len(false_positives)} 個")
    if false_positives:
        print("  假陽性明細（使用者會信任綠勾勾、不會逐筆檢查，這是最危險的錯誤）：")
        for line in false_positives:
            print(f"    - {line}")


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)

    workflow_path = Path(sys.argv[1])
    dataset_path = Path(sys.argv[2])
    answer_path = Path(sys.argv[3]) if len(sys.argv) == 4 else None

    paper_variables, target_col = load_paper_variables(workflow_path)
    user_columns = load_user_columns(dataset_path)

    print("=" * 70)
    print(f"論文變數 {len(paper_variables)} 個、資料表欄位 {len(user_columns)} 個")

    # ── 演算法層：字串比對 + 樣本值加減分 ──────────────────────────────────
    result = run_auto_mapping(paper_variables, user_columns)
    pending = [item for item in result["mapping_status"] if item["status"] != AUTO_MATCHED]
    print(f"\n[演算法層] 自動配對 {result['matched_count']} 個，待處理（非自動配對）{len(pending)} 個")

    # ── Gemini 穩定性：對同一批待處理項目連續呼叫 GEMINI_ROUNDS 次 ──────────
    print(f"\n[Gemini] 對 {len(pending)} 個待處理變數連續呼叫 semantic_match() {GEMINI_ROUNDS} 次，量測 JSON 解析成功率")
    service = GeminiService()
    successes = 0
    last_successful_suggestions: list[dict] = []
    for round_index in range(1, GEMINI_ROUNDS + 1):
        suggestions = service.semantic_match(pending, user_columns)
        if suggestions is None:
            print(f"  第 {round_index} 次：解析失敗（AI 不可用或回應無法解析）")
            continue
        successes += 1
        last_successful_suggestions = suggestions
        print(f"  第 {round_index} 次：成功，回傳 {len(suggestions)} 筆建議")
    print(f"  解析成功率：{successes}/{GEMINI_ROUNDS}")

    # 用「最後一次成功」的建議合併回對映表（跟 brief 的邏輯一致：沒有任何一次
    # 成功的話 last_successful_suggestions 維持空陣列，merge 形同 no-op）
    merge_semantic_suggestions(result, last_successful_suggestions, user_columns)

    print_mapping_table(result["mapping_status"])
    print_status_counts(result["mapping_status"])
    print_target_status(result["mapping_status"], target_col)

    print("\n" + "=" * 70)
    if answer_path is None:
        print("[準確率] 未提供人工答案卷，跳過準確率與假陽性計算。")
        print("         真實醫療資料的正確答案需要人工判斷，不能用腳本捏造——")
        print("         要算準確率，請另外準備 answer_json：{\"論文變數名\": \"正確欄位名或 null\"}，")
        print("         再帶第三個參數重跑本腳本。")
    else:
        answers = json.loads(answer_path.read_text(encoding="utf-8"))
        score_accuracy(result["mapping_status"], answers)


if __name__ == "__main__":
    main()
