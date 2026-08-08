"""寄信介面測試：目前實作只印到 log，之後要接真的 SMTP/SendGrid 時只需替換 send_reset_password_email 的實作。"""

import logging

from services.email_sender import send_reset_password_email


def test_send_reset_password_email_logs_recipient_and_link(caplog):
    with caplog.at_level(logging.INFO):
        send_reset_password_email(
            "user@example.com",
            "http://localhost:3000/reset-password?token=abc123",
        )

    assert "user@example.com" in caplog.text
    assert "http://localhost:3000/reset-password?token=abc123" in caplog.text
