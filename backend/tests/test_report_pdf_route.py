"""POST /api/report/<project_id>/pdf 路由測試：只測擁有權檢查/輸入驗證/回應檔頭，
不碰真的 WeasyPrint 轉檔（monkeypatch 掉），理由同 test_rag_routes.py 開頭註解。
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import routes.report as report_route  # noqa: E402
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


def test_download_pdf_rejects_project_not_owned(client, monkeypatch):
    monkeypatch.setattr(report_route, "_get_owned_project", lambda project_id: None)
    response = client.post("/api/report/7/pdf", json={"html": "<h1>x</h1>"})
    assert response.status_code == 404


def test_download_pdf_requires_html_field(client, monkeypatch):
    monkeypatch.setattr(report_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    response = client.post("/api/report/7/pdf", json={})
    assert response.status_code == 400


def test_download_pdf_returns_pdf_bytes_with_download_headers(client, monkeypatch):
    monkeypatch.setattr(report_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    monkeypatch.setattr("services.report.pdf_export.html_to_pdf", lambda html: b"%PDF-fake-bytes")

    response = client.post("/api/report/7/pdf", json={"html": "<h1>x</h1>", "filename": "我的論文"})

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data == b"%PDF-fake-bytes"
    assert "attachment" in response.headers["Content-Disposition"]


def test_download_pdf_returns_500_when_conversion_fails(client, monkeypatch):
    monkeypatch.setattr(report_route, "_get_owned_project", lambda project_id: FakeProject(project_id))

    def _raise(html):
        raise ValueError("boom")

    monkeypatch.setattr("services.report.pdf_export.html_to_pdf", _raise)

    response = client.post("/api/report/7/pdf", json={"html": "<h1>x</h1>"})

    assert response.status_code == 500
    assert response.get_json()["success"] is False


def test_download_pdf_requires_login(client_with_login_required):
    response = client_with_login_required.post("/api/report/7/pdf", json={"html": "<h1>x</h1>"})
    assert response.status_code == 401
