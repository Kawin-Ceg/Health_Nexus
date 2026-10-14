"""A person's settings, read the same way by the Settings page and by everything that sends them email."""

import copy
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError, model_validator

from app.models import User
from app.models.user import DEFAULT_PREFERENCES

from .triage import SEVERITY_RANK, Severity

HHMM = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class Channel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: bool


class Notifications(BaseModel):
    """Everything is always in the app (Alerts / Notifications). These choose what is also emailed."""

    model_config = ConfigDict(extra="forbid")
    alerts: Channel  # a flagged reading: the citizen's own, or one at the worker's centre
    visits: Channel  # booked, moved, cancelled, or waiting for an outcome


class WorkingHours(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: HHMM
    end: HHMM

    @model_validator(mode="after")
    def _ordered(self) -> "WorkingHours":
        if self.start >= self.end:
            raise ValueError("Working hours must end after they start")
        return self


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme: Literal["system", "light", "dark"]
    language: Literal["en", "ta", "hi"]
    notifications: Notifications
    # The least severe flag that is still emailed. "low" emails every flag.
    alert_email_min_severity: Severity
    working_hours: WorkingHours  # PHC workers: the default slot when booking a visit
    reading_reminders: bool  # citizens: one reminder after READING_REMINDER_AFTER without a reading


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _known(stored: dict[str, Any], shape: dict[str, Any]) -> dict[str, Any]:
    """Only the keys `shape` has, so settings retired since (SMS, language...) do not void the rest."""
    out: dict[str, Any] = {}
    for key, default in shape.items():
        if key not in stored:
            continue
        value = stored[key]
        if isinstance(default, dict):
            if isinstance(value, dict):
                out[key] = _known(value, default)
        else:
            out[key] = value
    return out


def current_preferences(user: User) -> Preferences:
    """Stored values over the defaults; anything stored that no longer validates falls back to the default."""
    stored = deep_merge(DEFAULT_PREFERENCES, _known(user.preferences or {}, DEFAULT_PREFERENCES))
    try:
        return Preferences.model_validate(stored)
    except ValidationError:
        return Preferences.model_validate(DEFAULT_PREFERENCES)


def emails_about(user: User, kind: Literal["alerts", "visits"]) -> bool:
    return user.is_active and getattr(current_preferences(user).notifications, kind).email


def emails_flag(user: User, severity: Severity) -> bool:
    """Emails about a flag of this severity: alerts are on and it is at least as severe as their minimum."""
    if not emails_about(user, "alerts"):
        return False
    return SEVERITY_RANK[severity] <= SEVERITY_RANK[current_preferences(user).alert_email_min_severity]
