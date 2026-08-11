"""寄信介面測試：SMTP 設定齊全時真的送信（用 mock 攔截，不連真的網路），沒設定時退回印到 log。

用 autouse fixture 清掉環境裡既有的 SMTP_* 變數，避免這支測試在本機/容器（backend/.env
若已設定真實 SMTP 帳密）意外連上真的 SMTP 伺服器、寄出真實郵件。
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from services.email_sender import send_reset_password_email


@pytest.fixture(autouse=True)
def clear_smtp_env(monkeypatch):
    for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.delenv(key, raising=False)


def test_send_reset_password_email_logs_recipient_and_link_without_smtp_config(caplog):
    with caplog.at_level(logging.INFO):
        send_reset_password_email(
            "user@example.com",
            "http://localhost:3000/reset-password?token=abc123",
        )

    assert "user@example.com" in caplog.text
    assert "http://localhost:3000/reset-password?token=abc123" in caplog.text


def test_send_reset_password_email_sends_via_smtp_when_configured(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")

    fake_server = MagicMock()
    fake_server.__enter__.return_value = fake_server

    with patch("services.email_sender.smtplib.SMTP", return_value=fake_server) as fake_smtp:
        send_reset_password_email(
            "user@example.com",
            "http://localhost:3000/reset-password?token=abc123",
        )

    fake_smtp.assert_called_once_with("smtp.example.com", 587)
    fake_server.starttls.assert_called_once()
    fake_server.login.assert_called_once_with("sender@example.com", "app-password")
    fake_server.send_message.assert_called_once()

    sent_message = fake_server.send_message.call_args[0][0]
    assert sent_message["To"] == "user@example.com"
    assert "http://localhost:3000/reset-password?token=abc123" in sent_message.get_content()
