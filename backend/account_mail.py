"""Small standard-library SMTP sender for account verification and recovery."""
from email.message import EmailMessage
import os
import smtplib
import ssl


def configured() -> bool:
    return all(os.environ.get(key, "").strip() for key in (
        "CROP_PULSE_SMTP_HOST", "CROP_PULSE_SMTP_FROM", "CROP_PULSE_PUBLIC_APP_URL",
    ))


def public_app_url() -> str:
    return os.environ.get("CROP_PULSE_PUBLIC_APP_URL", "").strip().rstrip("/")


def send_account_email(recipient: str, subject: str, text: str) -> None:
    if not configured():
        raise RuntimeError("Account email delivery is not configured.")
    host = os.environ["CROP_PULSE_SMTP_HOST"].strip()
    sender = os.environ["CROP_PULSE_SMTP_FROM"].strip()
    port = int(os.environ.get("CROP_PULSE_SMTP_PORT", "587"))
    username = os.environ.get("CROP_PULSE_SMTP_USERNAME", "").strip()
    password = os.environ.get("CROP_PULSE_SMTP_PASSWORD", "")
    use_ssl = os.environ.get("CROP_PULSE_SMTP_USE_SSL", "0").lower() in {"1", "true", "yes"}
    use_starttls = os.environ.get("CROP_PULSE_SMTP_STARTTLS", "1").lower() in {"1", "true", "yes"}
    if bool(username) != bool(password):
        raise RuntimeError("SMTP username and password must be configured together.")
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(text)
    context = ssl.create_default_context()
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=10, context=context) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_starttls:
                server.starttls(context=context)
            if username:
                server.login(username, password)
            server.send_message(message)
