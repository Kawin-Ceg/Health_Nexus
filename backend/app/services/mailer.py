"""Outgoing email: real SMTP when SMTP_HOST is set, otherwise the console.

Logs never carry a full address or a link; use mask_email() for anything logged.
The console fallback is the exception by design: it prints the whole message so
a developer can click the link without a mail server.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings

log = logging.getLogger(__name__)


def mask_email(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def _deliver_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    assert settings.SMTP_HOST
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def send_email(to: str, subject: str, body: str) -> None:
    """Never raises: a mail failure must not fail the request that triggered it."""
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    if not settings.SMTP_HOST:
        print(
            f"\n----- email (console, SMTP_HOST not set) -----\n"
            f"From: {settings.SMTP_FROM}\nTo: {to}\nSubject: {subject}\n\n{body}"
            f"----- end email -----\n",
            flush=True,
        )
        return
    try:
        await asyncio.to_thread(_deliver_smtp, message)
    except Exception as exc:  # noqa: BLE001 - smtplib raises many unrelated types
        log.error("Could not send email to %s (%s)", mask_email(to), type(exc).__name__)


def _link(path: str, token: str) -> str:
    return f"{get_settings().FRONTEND_URL.rstrip('/')}{path}?token={quote(token)}"


async def send_verification_email(to: str, name: str, token: str) -> None:
    await send_email(
        to,
        "Verify your HealthNexus email",
        f"Hi {name},\n\n"
        f"Confirm your email address to finish setting up your account:\n{_link('/verify-email', token)}\n\n"
        "This link works once and expires in 24 hours. You can open it on any device.\n"
        "If you did not create a HealthNexus account, ignore this message.\n",
    )


async def send_password_reset_email(to: str, name: str, token: str) -> None:
    await send_email(
        to,
        "Reset your HealthNexus password",
        f"Hi {name},\n\n"
        f"Choose a new password here:\n{_link('/reset-password', token)}\n\n"
        "This link works once and expires in 1 hour. Resetting signs you out everywhere.\n"
        "If you did not ask for this, ignore this message; your password has not changed.\n",
    )


async def send_email_change_email(to: str, name: str, token: str) -> None:
    await send_email(
        to,
        "Confirm your new HealthNexus email address",
        f"Hello {name},\n\n"
        f"Confirm this address to make it your HealthNexus sign-in email:\n{_link('/confirm-email', token)}\n\n"
        "This link works once and expires in 24 hours. Until you confirm, your old address keeps working.\n"
        "If you did not ask for this, ignore this message.\n",
    )


async def send_email_changed_notice(to: str, name: str, new_address: str) -> None:
    await send_email(
        to,
        "Your HealthNexus email address was changed",
        f"Hello {name},\n\n"
        f"Your HealthNexus sign-in email is now {mask_email(new_address)}. This address will no longer work for signing in.\n"
        "If you did not make this change, reset your password straight away and contact support.\n",
    )
