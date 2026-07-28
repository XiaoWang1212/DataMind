"""score_paper() 期刊評分手動驗證腳本

用法（在 backend/ 目錄下執行）：
    python scripts/test_score_paper.py
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

SAMPLE_PAPER_TEXT = """# 糖尿病再入院風險預測研究

## 摘要

本研究使用 XGBoost 模型對糖尿病病患的 30 天再入院風險進行預測，
在測試集上達到 AUC 0.96、F1 0.91，顯示模型具備良好的判別能力。

## 研究方法

資料集包含 12000 筆病患紀錄，類別分布為 9820:2180，使用 SMOTE 重採樣
處理類別不平衡問題，並以 train_test_split（80/20，stratified）進行驗證。

## 討論

本研究的限制在於資料僅來自單一醫院，模型的外推能力仍待更多中心驗證。
"""


def main():
    print("=" * 60)
    print("score_paper() 測試")
    print("=" * 60)

    from services.rag.paper_rag import PaperRAGService

    test_index_dir = BACKEND_DIR / "artifacts" / "test_score_index"
    test_index_dir.mkdir(parents=True, exist_ok=True)
    os.environ["RAG_INDEX_DIR"] = str(test_index_dir)

    service = PaperRAGService()

    result = service.score_paper(SAMPLE_PAPER_TEXT)
    print(f"\nsuccess: {result['success']}")
    assert result["success"], f"至少要有一個期刊評分成功：{result}"

    print(f"failed_journals: {result['failed_journals']}")
    assert len(result["journal_scores"]) + len(result["failed_journals"]) == 3, \
        "journal_scores + failed_journals 應等於期刊總數 3"

    for js in result["journal_scores"]:
        print(f"\n▶ {js['journal']}（總分 {js['overall_score']}）")
        assert 0 <= js["overall_score"] <= 100
        assert len(js["criteria"]) == 6, f"應有 6 項準則：{js['criteria']}"
        for c in js["criteria"]:
            assert 0 <= c["score"] <= 100
            print(f"    - {c['name']}: {c['score']} — {c['comment'][:40]}...")
        assert len(js["suggestions"]) >= 1, "至少要有一條修改建議"

    print("\n測試完成！")


if __name__ == "__main__":
    main()
