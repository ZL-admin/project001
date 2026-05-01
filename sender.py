"""
Sends the daily HTML digest via SMTP email.
Supports Gmail (App Password) and QQ/163 mail.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

logger = logging.getLogger(__name__)

EMAIL_SUBJECTS = {
    "default": "🤖 具身智能&人形机器人 全球日报 · {date}",
}


def send_email(
    html_content: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    recipient: str,
    sender_name: str = "机器人日报",
) -> None:
    today = date.today().strftime("%Y年%m月%d日")
    subject = EMAIL_SUBJECTS["default"].format(date=today)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{smtp_user}>"
    msg["To"] = recipient

    # Plain text fallback
    plain_text = (
        f"具身智能&人形机器人 全球日报 · {today}\n\n"
        "请使用支持 HTML 的邮件客户端查看完整排版。\n\n"
        "或访问本地网页：http://localhost:5000"
    )
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    use_ssl = smtp_port == 465
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [recipient], msg.as_bytes())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [recipient], msg.as_bytes())
        logger.info(f"Email sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise
