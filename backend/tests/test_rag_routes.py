"""路由層測試：只測 project_id 驗證/擁有權檢查/登入檢查，不碰資料庫、不碰真的 PaperRAGService
（monkeypatch 掉），理由同 test_field_mapping_routes.py 開頭註解。
"""

import os
from urllib.error import URLError

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import routes.rag as rag_route  # noqa: E402
import services.rag.paper_rag as paper_rag_module  # noqa: E402
from apps import create_app  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    return app.test_client()


@pytest.fixture
def client_with_login_required():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class FakeProject:
    def __init__(self, project_id=7, user_id=1):
        self.id = project_id
        self.user_id = user_id


class FakeService:
    def __init__(self):
        self.calls = []

    def search(self, project_id, query, top_k=5, use_rerank=True):
        self.calls.append(("search", project_id))
        return []

    def get_status(self, project_id):
        self.calls.append(("get_status", project_id))
        return {"total_papers": 0, "total_chunks": 0}

    def add_paper(self, project_id, title, content, metadata=None):
        self.calls.append(("add_paper", project_id))
        return {"success": True, "paper_id": "1", "title": title, "chunks_added": 1}

    def generate_citation(self, project_id, query, top_k=3, citation_style="apa"):
        self.calls.append(("generate_citation", project_id))
        return {"citations": [], "sources": []}

    def clear(self, project_id):
        self.calls.append(("clear", project_id))
        return {"success": True, "message": "已清空論文庫"}

    def delete_paper(self, project_id, paper_id):
        self.calls.append(("delete_paper", project_id, paper_id))
        return {"success": True, "message": "已刪除論文"}

    def generate_paper(self, project_id, topic, mining_results, structure=None, language="zh-TW"):
        self.calls.append(("generate_paper", project_id))
        return {
            "paper_markdown": "", "citation_map": [], "references": [],
            "citation_report": "", "sections_generated": [], "usage": {},
        }

    def ingest_arxiv_selection(self, project_id, candidates):
        self.calls.append(("ingest_arxiv_selection", project_id))
        return {"success": True, "ingested": [], "failed": []}

    def search_arxiv_candidates(self, mining_results, user_title):
        self.calls.append(("search_arxiv_candidates", user_title))
        return {"topic": "t", "arxiv_query": "q", "candidates": []}


class FakeServiceRaising:
    """search_arxiv_candidates / ingest_arxiv_selection 拋出指定例外，模擬 arXiv 逾時/連線失敗。"""

    def __init__(self, error):
        self._error = error

    def search_arxiv_candidates(self, mining_results, user_title):
        raise self._error

    def ingest_arxiv_selection(self, project_id, candidates):
        raise self._error


MISSING_PROJECT_ID_CASES = [
    ("post", "/api/rag/upload", {"json": {"title": "t", "content": "c"}}),
    ("post", "/api/rag/search", {"json": {"query": "q"}}),
    ("post", "/api/rag/cite", {"json": {"query": "q"}}),
    ("get", "/api/rag/status", {}),
    ("post", "/api/rag/clear", {"json": {}}),
    ("delete", "/api/rag/paper/1", {}),
    ("post", "/api/rag/generate-paper", {"json": {"topic": "t", "mining_results": {}}}),
    (
        "post", "/api/rag/arxiv/generate",
        {"json": {"topic": "t", "mining_results": {}, "selected_candidates": [{}]}},
    ),
]


@pytest.mark.parametrize("method,path,kwargs", MISSING_PROJECT_ID_CASES)
def test_missing_project_id_returns_400(client, method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_search_rejects_project_not_owned(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: None)
    response = client.post("/api/rag/search", json={"project_id": 7, "query": "q"})
    assert response.status_code == 404


def test_search_delegates_with_project_id(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/search", json={"project_id": 7, "query": "deep learning"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert fake_service.calls == [("search", 7)]


def test_status_reads_project_id_from_query_string(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.get("/api/rag/status?project_id=7")

    assert response.status_code == 200
    assert fake_service.calls == [("get_status", 7)]


def test_delete_paper_reads_project_id_from_query_string(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.delete("/api/rag/paper/42?project_id=7")

    assert response.status_code == 200
    assert fake_service.calls == [("delete_paper", 7, "42")]


def test_search_requires_login(client_with_login_required):
    response = client_with_login_required.post(
        "/api/rag/search", json={"project_id": 1, "query": "q"}
    )
    assert response.status_code == 401


# search_arxiv_candidates/ingest_arxiv_selection 逾時或連線失敗時，路由層要換成
# 好懂的中文訊息，不能把 Python 原始例外字串（例如 "The read operation timed
# out"）直接丟給前端 —— 那看起來像系統壞掉而不是「網路慢，可以重試」。
ARXIV_TIMEOUT_CASES = [
    (
        "/api/rag/arxiv/search",
        {"mining_results": {}},
    ),
    (
        "/api/rag/arxiv/generate",
        {"project_id": 7, "topic": "t", "mining_results": {}, "selected_candidates": [{}]},
    ),
]


@pytest.mark.parametrize("path,payload", ARXIV_TIMEOUT_CASES)
@pytest.mark.parametrize("error", [TimeoutError("The read operation timed out"), URLError("timed out")])
def test_arxiv_route_returns_friendly_message_on_network_timeout(client, monkeypatch, path, payload, error):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeServiceRaising(error)
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post(path, json=payload)

    assert response.status_code == 504
    body = response.get_json()
    assert body["success"] is False
    assert "逾時" in body["error"]
    assert "read operation timed out" not in body["error"]
