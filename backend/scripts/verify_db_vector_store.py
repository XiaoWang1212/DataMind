"""手動驗證：DbVectorStore 直接操作（不經過 HTTP），需要真的 Postgres + app context。

執行方式（docker-compose 要先啟動）：
    MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_db_vector_store.py

會借用資料庫裡第一個既有的 user 建立兩個測試用 project，跑完自動清理（連帶刪除
建立的論文，靠 migration 加的 ON DELETE CASCADE）。如果資料庫完全沒有 user，
先跑過 backend/scripts/seed_admin.py 建一個。
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from apps import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models.project import Project  # noqa: E402
from models.user import User  # noqa: E402
from services.rag.chunker import TextChunker  # noqa: E402
from services.rag.db_vector_store import DbVectorStore  # noqa: E402
from services.rag.embedder import Embedder  # noqa: E402


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    app = create_app()
    with app.app_context():
        user = User.query.first()
        if user is None:
            raise SystemExit("資料庫沒有任何 user，先跑 backend/scripts/seed_admin.py")

        created_project_ids: list[int] = []
        try:
            project = Project(user_id=user.id, name="verify_db_vector_store")
            db.session.add(project)
            db.session.commit()
            created_project_ids.append(project.id)
            project_id = project.id

            other_project = Project(user_id=user.id, name="verify_db_vector_store (other)")
            db.session.add(other_project)
            db.session.commit()
            created_project_ids.append(other_project.id)

            embedder = Embedder()
            print(f"embedder backend: {embedder.backend}")
            store = DbVectorStore(embedder=embedder)
            chunker = TextChunker()

            paper_id = store.create_paper(
                project_id, "Verify Paper",
                {"author": "Tester", "year": "2024", "arxiv_id": "9999.99999"},
            )
            check("create_paper 回傳字串 paper_id", isinstance(paper_id, str))

            chunks = chunker.chunk(
                "Deep learning models improve medical diagnosis accuracy significantly. "
                "Convolutional neural networks are widely used for image classification tasks.",
                paper_id=paper_id, title="Verify Paper", metadata={},
            )
            store.add_chunks(chunks)
            check("add_chunks 沒有拋例外", True)

            results = store.search(project_id, "deep learning diagnosis", top_k=3)
            check("search 找得到剛存進去的段落", len(results) > 0)
            check("search 回傳的 Chunk.title 正確", results and results[0][0].title == "Verify Paper")

            empty_results = store.search(other_project.id, "deep learning diagnosis", top_k=3)
            check("不同 project 搜不到（隔離生效）", len(empty_results) == 0)

            found = store.find_by_arxiv_id(project_id, "9999.99999")
            check("find_by_arxiv_id 找得到剛存的論文", found is not None and str(found.id) == paper_id)

            not_found = store.find_by_arxiv_id(other_project.id, "9999.99999")
            check("find_by_arxiv_id 在別的 project 找不到", not_found is None)

            status = store.get_status(project_id)
            check("get_status 回報 1 篇論文", status["total_papers"] == 1)
            check("get_status 回報 chunks 數量 > 0", status["total_chunks"] > 0)

            deleted = store.delete_paper(project_id, paper_id)
            check("delete_paper 成功", deleted is True)

            after_delete = store.search(project_id, "deep learning diagnosis", top_k=3)
            check("刪除後搜不到（chunks 被 cascade 一併刪除）", len(after_delete) == 0)

            deleted_again = store.delete_paper(project_id, paper_id)
            check("重複刪除同一篇回傳 False", deleted_again is False)
        finally:
            for pid in created_project_ids:
                p = Project.query.get(pid)
                if p:
                    db.session.delete(p)
            db.session.commit()

    print("\n全部通過。")


if __name__ == "__main__":
    main()
