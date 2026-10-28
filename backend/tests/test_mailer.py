import logging

from app.services import mailer
from app.services.mailer import mask_email, send_verification_email


def test_mask_email_keeps_only_the_first_letter():
    assert mask_email("asha@example.com") == "a***@example.com"
    assert mask_email("nonsense") == "***"


async def test_console_fallback_prints_a_link_that_can_be_copied_intact(capsys):
    token = "abcDEF123_-" * 4
    await send_verification_email("asha@example.com", "Asha", token)
    out = capsys.readouterr().out
    assert f"/verify-email?token={token}\n" in out
    assert "=3D" not in out and "To: asha@example.com" in out


async def test_a_failed_send_never_raises_and_logs_no_full_address(monkeypatch, caplog):
    monkeypatch.setenv("SMTP_HOST", "smtp.invalid")
    from app.core.config import get_settings

    get_settings.cache_clear()

    def boom(message):
        raise OSError("refused for asha@example.com")

    monkeypatch.setattr(mailer, "_deliver_smtp", boom)
    try:
        with caplog.at_level(logging.ERROR):
            await mailer.send_email("asha@example.com", "Subject", "Body")
    finally:
        monkeypatch.delenv("SMTP_HOST")
        get_settings.cache_clear()
    assert "asha@example.com" not in caplog.text and "a***@example.com" in caplog.text
