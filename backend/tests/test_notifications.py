"""Email notifications follow Settings > Preferences, and reading reminders come once per quiet stretch."""

from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.models import Alert, HealthRecord, User
from app.models.base import utcnow
from app.models.enums import UserRole
from app.services import notify, reminders
from app.services.preferences import current_preferences, emails_flag

from .conftest import BASE
from .test_modules import HIGH_BP, NORMAL, make_user, submit, world  # noqa: F401  (world is a fixture)


@pytest.fixture
def sent(monkeypatch) -> list[tuple[str, str, str]]:
    box: list[tuple[str, str, str]] = []

    async def capture(to: str, subject: str, body: str) -> None:
        box.append((to, subject, body))

    monkeypatch.setattr(notify, "send_email", capture)
    return box


async def emails(sent):
    await notify.drain()
    return sent


async def test_a_flag_emails_the_citizen_and_their_workers(client, world, sent):
    priya, ph = world["priya"]
    worker, _ = world["worker"]
    other, _ = world["other_worker"]
    await submit(client, ph, NORMAL)
    assert await emails(sent) == []

    await submit(client, ph, HIGH_BP)
    out = {to: (subject, body) for to, subject, body in await emails(sent)}
    assert set(out) == {priya.email, worker.email}
    assert "flagged" in out[priya.email][0]
    assert "Priya" not in out[worker.email][1] and "167" not in out[worker.email][1]
    assert other.email not in out


async def test_email_choices_are_respected(client, world, sent):
    priya, ph = world["priya"]
    worker, wh = world["worker"]
    await client.patch(f"{BASE}/settings/preferences", json={"notifications": {"alerts": {"email": False}}}, headers=ph)
    await client.patch(f"{BASE}/settings/preferences", json={"notifications": {"alerts": {"email": False}}}, headers=wh)
    await submit(client, ph, HIGH_BP)
    assert await emails(sent) == []


def test_the_severity_floor():
    person = User(is_active=True, preferences={"alert_email_min_severity": "high"})
    assert [s for s in ("critical", "high", "moderate", "low") if emails_flag(person, s)] == ["critical", "high"]
    person.is_active = False
    assert not emails_flag(person, "critical")


async def test_a_failed_request_sends_nothing(db, world, sent):
    priya, _ = world["priya"]
    await db.execute(select(1))
    notify.queue_email(db, priya.email, "x", "y")
    await db.rollback()
    await db.commit()
    assert await emails(sent) == []


async def test_visit_emails(client, db, world, sent):
    priya, ph = world["priya"]
    worker, wh = world["worker"]
    await client.patch(f"{BASE}/settings/preferences", json={"notifications": {"visits": {"email": False}}}, headers=wh)
    r = await client.post(
        f"{BASE}/phc/visits",
        json={"citizen_id": str(priya.id), "scheduled_for": (utcnow() + timedelta(days=2)).isoformat(), "reason": "BP check"},
        headers=wh,
    )
    assert r.status_code == 201, r.text
    assert [(to, subject) for to, subject, _ in await emails(sent)] == [(priya.email, "A health centre visit is booked")]


async def test_retired_settings_are_ignored_not_fatal(db, world):
    priya, _ = world["priya"]
    priya.preferences = {
        "theme": "dark",
        "language": "ta",
        "notifications": {"alerts": {"email": False, "sms": True, "in_app": True}, "announcements": {"email": True}},
        "alert_threshold": 40,
    }
    prefs = current_preferences(priya)
    assert prefs.theme == "dark" and prefs.notifications.alerts.email is False
    assert prefs.notifications.visits.email is True and prefs.reading_reminders is True


async def test_reading_reminders_come_once_per_quiet_stretch(client, db, world, sent):
    priya, ph = world["priya"]
    ravi, rh = world["ravi"]
    await submit(client, ph, NORMAL)
    await submit(client, rh, NORMAL)
    await client.patch(f"{BASE}/settings/preferences", json={"reading_reminders": False}, headers=rh)
    four_days_ago = utcnow() - timedelta(days=4)
    await db.execute(update(User).where(User.role == UserRole.user).values(created_at=four_days_ago))
    await db.execute(update(HealthRecord).values(timestamp=four_days_ago))
    await db.commit()

    assert await reminders.send_due(db) == 2
    reminded = {to for to, _, _ in await emails(sent)}
    assert priya.email in reminded and world["foreign"][0].email in reminded and ravi.email not in reminded
    assert await reminders.send_due(db) == 0
    assert any("since your last reading" in m for m in await db.scalars(select(Alert.message).where(Alert.user_id == priya.id)))

    await submit(client, ph, NORMAL)
    assert await reminders.send_due(db) == 0
