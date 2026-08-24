"""手動驗證：兩個不同帳號、不同 project，RAG 論文索引完全互相隔離。

執行方式（docker-compose 要先啟動，backend 服務對外開在 5002 → 容器內 5001，
所以從容器內執行用 5001）：
    MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_rag_project_isolation.py

會自建兩個測試帳號、兩個 project、上傳一篇論文，全部是真實 HTTP 請求（跟前端呼叫
的路徑完全一樣）。留下的測試帳號不會自動刪除（沒有帳號刪除 API），但都是明顯的
測試用 email，不影響正常使用者資料。
"""

import os
import uuid

import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001")


def register_and_login(email: str) -> requests.Session:
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "test-password-123", "displayName": "RAG isolation test"},
    )
    assert resp.status_code == 200, f"register failed: {resp.status_code} {resp.text}"
    return session


def create_project(session: requests.Session, name: str) -> int:
    resp = session.post(f"{BASE_URL}/api/projects", json={"name": name})
    assert resp.status_code == 200, f"create project failed: {resp.status_code} {resp.text}"
    return resp.json()["result"]["id"]


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    session_a = register_and_login(f"rag-isolation-a-{suffix}@test.local")
    session_b = register_and_login(f"rag-isolation-b-{suffix}@test.local")

    project_a = create_project(session_a, "RAG isolation test A")
    project_b = create_project(session_b, "RAG isolation test B")

    upload_resp = session_a.post(
        f"{BASE_URL}/api/rag/upload",
        json={
            "project_id": project_a,
            "title": "Isolation Test Paper",
            "content": (
                "Deep learning models improve medical diagnosis accuracy significantly. "
                "Convolutional neural networks are widely used for image classification tasks."
            ),
            "author": "Test Author",
            "year": "2024",
        },
    )
    check("A 上傳論文成功", upload_resp.status_code == 200 and upload_resp.json().get("success") is True)
    paper_id = upload_resp.json()["result"]["paper_id"]

    search_a = session_a.post(
        f"{BASE_URL}/api/rag/search",
        json={"project_id": project_a, "query": "deep learning medical diagnosis", "top_k": 3},
    )
    check(
        "A 在自己的 project 搜得到剛上傳的論文",
        search_a.status_code == 200 and len(search_a.json().get("results", [])) > 0,
    )

    search_b = session_b.post(
        f"{BASE_URL}/api/rag/search",
        json={"project_id": project_b, "query": "deep learning medical diagnosis", "top_k": 3},
    )
    check(
        "B 在自己的 project 搜不到 A 上傳的論文（隔離生效）",
        search_b.status_code == 200 and len(search_b.json().get("results", [])) == 0,
    )

    search_cross = session_b.post(
        f"{BASE_URL}/api/rag/search",
        json={"project_id": project_a, "query": "deep learning", "top_k": 3},
    )
    check("B 不能用 A 的 project_id 搜尋（回 404）", search_cross.status_code == 404)

    delete_cross = session_b.delete(
        f"{BASE_URL}/api/rag/paper/{paper_id}", params={"project_id": project_a}
    )
    check("B 不能刪除 A 的論文（回 404）", delete_cross.status_code == 404)

    delete_own = session_a.delete(
        f"{BASE_URL}/api/rag/paper/{paper_id}", params={"project_id": project_a}
    )
    check("A 刪除自己的論文成功", delete_own.status_code == 200 and delete_own.json().get("success") is True)

    session_a.post(f"{BASE_URL}/api/rag/clear", json={"project_id": project_a})
    session_b.post(f"{BASE_URL}/api/rag/clear", json={"project_id": project_b})

    print("\n全部通過。")


if __name__ == "__main__":
    main()
