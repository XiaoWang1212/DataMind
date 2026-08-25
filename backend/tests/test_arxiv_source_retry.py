"""search_arxiv() 對逾時/連線失敗的重試行為。

arXiv 的 Export API 從這個環境常常要嘗試幾次才會成功（2026-08-24 的逾時事故：
urllib.request.urlopen 15 秒讀取逾時），加重試比直接放棄使用者體驗好很多；但
真的收到 HTTP 錯誤狀態碼（HTTPError，例如 400）重試沒有意義，直接往外拋，不
要浪費時間重試一個不會變好的請求。
"""

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from services.rag.arxiv_source import search_arxiv

_SAMPLE_ATOM_RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <title>A Sample Paper</title>
    <summary>An abstract.</summary>
    <published>2023-01-01T00:00:00Z</published>
    <author><name>Jane Doe</name></author>
    <link title="pdf" href="https://arxiv.org/pdf/1234.5678v1"/>
  </entry>
</feed>"""


def _fake_response(body: bytes):
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class TestSearchArxivRetry:
    def test_succeeds_immediately_when_first_call_works(self):
        with patch(
            "services.rag.arxiv_source.urllib.request.urlopen",
            return_value=_fake_response(_SAMPLE_ATOM_RESPONSE),
        ) as fake_urlopen:
            results = search_arxiv("machine learning")

        assert fake_urlopen.call_count == 1
        assert results[0]["title"] == "A Sample Paper"

    def test_retries_after_timeout_then_succeeds(self):
        with patch(
            "services.rag.arxiv_source.urllib.request.urlopen",
            side_effect=[TimeoutError("The read operation timed out"), _fake_response(_SAMPLE_ATOM_RESPONSE)],
        ) as fake_urlopen, patch("services.rag.arxiv_source.time.sleep") as fake_sleep:
            results = search_arxiv("machine learning")

        assert fake_urlopen.call_count == 2
        assert fake_sleep.call_count == 1
        assert results[0]["title"] == "A Sample Paper"

    def test_retries_after_connection_error_then_succeeds(self):
        with patch(
            "services.rag.arxiv_source.urllib.request.urlopen",
            side_effect=[URLError("timed out"), _fake_response(_SAMPLE_ATOM_RESPONSE)],
        ) as fake_urlopen, patch("services.rag.arxiv_source.time.sleep"):
            results = search_arxiv("machine learning")

        assert fake_urlopen.call_count == 2
        assert results[0]["title"] == "A Sample Paper"

    def test_raises_after_exhausting_all_retries(self):
        with patch(
            "services.rag.arxiv_source.urllib.request.urlopen",
            side_effect=TimeoutError("The read operation timed out"),
        ) as fake_urlopen, patch("services.rag.arxiv_source.time.sleep"):
            with pytest.raises(TimeoutError):
                search_arxiv("machine learning")

        assert fake_urlopen.call_count == 3

    def test_does_not_retry_on_http_error_response(self):
        http_error = HTTPError(url="x", code=400, msg="Bad Request", hdrs=None, fp=None)
        with patch(
            "services.rag.arxiv_source.urllib.request.urlopen", side_effect=http_error,
        ) as fake_urlopen:
            with pytest.raises(HTTPError):
                search_arxiv("machine learning")

        assert fake_urlopen.call_count == 1
