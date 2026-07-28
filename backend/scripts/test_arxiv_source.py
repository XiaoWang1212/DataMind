"""arxiv_source.py 手動驗證腳本(用法：在 backend/ 目錄下執行 python scripts/test_arxiv_source.py）"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.rag.arxiv_source import fetch_pdf_text, search_arxiv


def main():
    print("=" * 60)
    print("[Step 1] 查詢 arXiv: 'XGBoost customer churn prediction imbalanced classification'")
    candidates = search_arxiv("XGBoost customer churn prediction imbalanced classification", max_results=3)
    assert len(candidates) > 0, "應該至少查到一篇論文"

    for c in candidates:
        print(f"\n[{c['arxiv_id']}] {c['title']} ({c['year']})")
        print(f"  作者：{c['authors']}")
        print(f"  摘要：{c['abstract'][:120]}...")
        print(f"  PDF：{c['pdf_url']}")
        assert c["pdf_url"], "每篇候選論文都應該有 pdf_url"

    print("\n[Step 2] 下載並解析第一篇的 PDF 全文...")
    text = fetch_pdf_text(candidates[0]["pdf_url"])
    print(f"  解析出全文長度：{len(text)} 字元")
    assert len(text) > 500, "全文長度應該遠超過摘要長度"

    print("\n測試完成！")


if __name__ == "__main__":
    main()
