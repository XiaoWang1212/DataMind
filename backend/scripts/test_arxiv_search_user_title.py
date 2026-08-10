"""手動驗證腳本：classify_topic() 在有/無 user_title 時的行為。

會真的呼叫 Gemini API（需要 GEMINI_API_KEY），不進 pytest 自動收集範圍
（backend/pyproject.toml 的 testpaths 已排除 scripts/）。用法：

    docker exec datamind-backend uv run python scripts/test_arxiv_search_user_title.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.rag.paper_rag import get_paper_rag_service  # noqa: E402

FAKE_MINING_RESULTS = {
    "class_distribution": {"counts": {"流失": 320, "未流失": 1680}, "imbalance_ratio": 5.25},
    "results": [
        {
            "preprocess_pipeline_index": 0,
            "preprocess_steps": [{"type": "標準化"}],
            "feature_engineering_steps": [{"type": "One-Hot 編碼"}],
        },
    ],
}


def main() -> None:
    service = get_paper_rag_service()

    print("=== 情境 1：無 user_title（維持現有全自動推論行為）===")
    result_auto = service.classify_topic(FAKE_MINING_RESULTS)
    print(f"topic: {result_auto['topic']}")
    print(f"arxiv_query: {result_auto['arxiv_query']}")
    assert result_auto["topic"], "無標題情境下 topic 不應該是空字串"
    assert result_auto["arxiv_query"], "無標題情境下 arxiv_query 不應該是空字串"

    print()
    print("=== 情境 2：有 user_title（主題直接採用使用者輸入）===")
    user_title = "機器學習於電信客戶流失預測之特徵重要性分析"
    result_titled = service.classify_topic(FAKE_MINING_RESULTS, user_title)
    print(f"topic: {result_titled['topic']}")
    print(f"arxiv_query: {result_titled['arxiv_query']}")
    assert result_titled["topic"] == user_title, "有標題情境下 topic 必須完全等於使用者輸入"
    assert result_titled["arxiv_query"], "有標題情境下 arxiv_query 不應該是空字串"
    assert result_titled["arxiv_query"] != result_auto["arxiv_query"], (
        "有標題跟無標題理論上應該問出不同的查詢字（人工檢查這條的合理性，"
        "非嚴格保證，Gemini 有極小機率剛好給出一樣的關鍵字）"
    )

    print()
    print("全部情境通過。")


if __name__ == "__main__":
    main()
