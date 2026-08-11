"""可插拔的寄信介面。

有設定 SMTP_HOST/SMTP_USER/SMTP_PASSWORD 時透過 SMTP 實際寄出重設密碼信；
沒有設定時（例如其他開發者尚未申請信箱憑證）退回印到 log，讓忘記密碼流程
在沒有寄信服務的環境下仍然可以測試。呼叫端（backend/routes/auth.py）
不需要因為換寄信方式而修改。
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_reset_password_email(to: str, reset_link: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_password:
        logger.info("[password-reset] to=%s link=%s", to, reset_link)
        return

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("SMTP_FROM", smtp_user)

    message = EmailMessage()
    message["Subject"] = "DataMind 重設密碼"
    message["From"] = from_addr
    message["To"] = to
    message.set_content(
        "我們收到重設你 DataMind 密碼的請求。\n\n"
        f"請點擊以下連結重設密碼：\n{reset_link}\n\n"
        "此連結將於 1 小時後失效。如果你沒有申請重設密碼，請忽略這封信。"
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

    logger.info("[password-reset] sent to=%s", to)
