"""SMTP delivery; credentials and reset links must never enter logs."""
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def send_reset_email(recipient: str, reset_url: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Reset your Daymark password"
    message["From"] = str(settings.smtp_from)
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your Daymark account.\n\n"
        f"Open this link to choose a new password:\n{reset_url}\n\n"
        f"This link expires in {settings.reset_token_ttl_minutes} minutes and works only once.\n"
        "If you did not request this, ignore this email. Your password has not changed.\n"
    )
    context = ssl.create_default_context()
    if settings.smtp_tls_mode == "ssl":
        connection = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port,
                                     timeout=settings.smtp_timeout_seconds, context=context)
    else:
        connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port,
                                 timeout=settings.smtp_timeout_seconds)
    with connection as smtp:
        if settings.smtp_tls_mode == "starttls":
            smtp.starttls(context=context)
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
