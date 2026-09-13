"""Sends the expected-purchase-items alert by email (Gmail SMTP)."""
import logging
import smtplib
from email.message import EmailMessage

from zentrada_alert import config
from zentrada_alert.scraper import Product

logger = logging.getLogger(__name__)


def build_email(products: list[Product]) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"[Zentrada] 구매예상 품목 알림 ({len(products)}건)"
    message["From"] = config.EMAIL_ADDRESS
    message["To"] = config.EMAIL_TO

    text_lines = ["구매가 예상되는 품목을 안내드립니다.\n"]
    html_rows = []
    for product in products:
        text_lines.append(f"- {product.name} | {product.price} | {product.url}")
        html_rows.append(
            "<tr>"
            f"<td>{product.name}</td>"
            f"<td>{product.price}</td>"
            f'<td><a href="{product.url}">바로가기</a></td>'
            "</tr>"
        )

    message.set_content("\n".join(text_lines))
    message.add_alternative(
        "<html><body>"
        "<p>구매가 예상되는 품목을 안내드립니다.</p>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>상품명</th><th>가격</th><th>링크</th></tr>"
        f"{''.join(html_rows)}"
        "</table>"
        "</body></html>",
        subtype="html",
    )
    return message


def send_alert(products: list[Product]) -> None:
    if not products:
        logger.info("No matching products; skipping email.")
        return

    if not config.EMAIL_ADDRESS or not config.EMAIL_APP_PASSWORD:
        raise RuntimeError(
            "EMAIL_ADDRESS / EMAIL_APP_PASSWORD is not configured. "
            "Set them in your .env (use a Gmail App Password, not your login password)."
        )

    message = build_email(products)

    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        smtp.send_message(message)

    logger.info("Sent alert email for %d product(s).", len(products))
