"""可插拔的寄信介面。

目前的實作只把重設連結印到 log，方便本地開發測試。
之後要接真的 SMTP/SendGrid 等服務時，只需要替換這支函式的內容，
呼叫端（backend/routes/auth.py）不需要修改。
"""

import logging

logger = logging.getLogger(__name__)


def send_reset_password_email(to: str, reset_link: str) -> None:
    logger.info("[password-reset] to=%s link=%s", to, reset_link)
