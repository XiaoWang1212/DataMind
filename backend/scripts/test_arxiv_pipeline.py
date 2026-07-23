"""arXiv 分類/查詢/入庫 pipeline 手動驗證腳本

用法（在 backend/ 目錄下執行）：
    python scripts/test_arxiv_pipeline.py
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

# 跟 test_paper_gen.py 相同形狀的假 DataMind 輸出
MOCK_DATAMIND_OUTPUT = {
    "success": True,
    "class_distribution": {
        "counts": {"0": 9820, "1": 2180},
        "imbalance_ratio": 4.5046
    },
    "preprocess_variants": [
        {
            "preprocess_steps": [
                {"type": "fill_na", "strategy": "mean"},
                {"type": "standardize"}
            ],
            "feature_engineering_steps": [
                {"type": "select_relevant_features", "k": 20}
            ]
        }
    ],
    "results": [
        {
            "preprocess_pipeline_index": 0,
            "model_name": "XGBoost",
            "split_name": "split_0",
            "validation_config": {
                "method": "train_test_split",
                "n_splits": 1,
                "stratified": True,
                "train_size": 0.8,
                "test_size": 0.2,
                "shuffle": True,
                "random_state": 42
            },
            "resampling_method": "smote",
            "best_params": {},
            "metrics": [
                {"id": "s0", "metric": "balanced_accuracy", "value": 0.9420, "ci_lower": None, "ci_upper": None},
                {"id": "s1", "metric": "auc", "value": 0.9601, "ci_lower": None, "ci_upper": None},
                {"id": "s2", "metric": "precision", "value": 0.93, "ci_lower": None, "ci_upper": None},
                {"id": "s3", "metric": "recall", "value": 0.89, "ci_lower": None, "ci_upper": None},
                {"id": "s4", "metric": "f1", "value": 0.91, "ci_lower": None, "ci_upper": None},
            ],
        },
    ]
}


def main():
    print("=" * 60)
    print("arXiv Pipeline 測試")
    print("=" * 60)

    from services.rag.paper_rag import PaperRAGService

    test_index_dir = BACKEND_DIR / "artifacts" / "test_arxiv_index"
    test_index_dir.mkdir(parents=True, exist_ok=True)
    os.environ["RAG_INDEX_DIR"] = str(test_index_dir)

    service = PaperRAGService()

    print("\n[Step 1] 分類 mining_results 並查詢 arXiv 候選論文...")
    search_result = service.search_arxiv_candidates(MOCK_DATAMIND_OUTPUT)
    print(f"  研究主題：{search_result['topic']}")
    print(f"  arXiv 查詢字串：{search_result['arxiv_query']}")
    print(f"  候選論文數：{len(search_result['candidates'])}")
    assert len(search_result["candidates"]) > 0, "應該至少查到一篇候選論文"

    for c in search_result["candidates"][:3]:
        print(f"    - [{c['arxiv_id']}] {c['title']}")

    print("\n[Step 2] 選前 2 篇候選論文，下載全文入庫...")
    selected = search_result["candidates"][:2]
    ingest_result = service.ingest_arxiv_selection(selected)
    print(f"  入庫成功：{ingest_result['ingested']}")
    print(f"  入庫失敗：{ingest_result['failed']}")
    assert ingest_result["success"], f"入庫應該至少成功一篇：{ingest_result}"

    status = service.get_status()
    print(f"  向量庫狀態：{status['total_papers']} 篇論文，{status['total_chunks']} 個 chunks")

    print("\n測試完成！")


if __name__ == "__main__":
    main()
