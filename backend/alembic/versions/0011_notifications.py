"""users: new preferences default, and when a reading reminder was last sent

The preferences JSON loses the settings nothing acted on (language, SMS, in-app
switches, the numeric alert threshold) and gains visit emails, an email severity
floor and reading reminders. Stored rows are not rewritten: unknown keys are
ignored when read (services/preferences.py), so each person's alert email choice
carries over.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-13
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_DEFAULT = {
    "theme": "light",
    "notifications": {"alerts": {"email": True}, "visits": {"email": True}},
    "alert_email_min_severity": "low",
    "working_hours": {"start": "09:00", "end": "17:00"},
    "reading_reminders": True,
}
OLD_DEFAULT = {
    "theme": "light",
    "language": "en",
    "notifications": {
        "alerts": {"email": True, "sms": False, "in_app": True},
        "surveillance": {"email": False, "sms": False, "in_app": True},
        "announcements": {"email": True, "sms": False, "in_app": True},
    },
    "alert_threshold": 70,
    "working_hours": {"start": "09:00", "end": "17:00"},
    "resubmission_reminders": True,
}


def upgrade() -> None:
    op.add_column("users", sa.Column("reading_reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "preferences", server_default=sa.text(f"'{json.dumps(NEW_DEFAULT)}'"))


def downgrade() -> None:
    op.alter_column("users", "preferences", server_default=sa.text(f"'{json.dumps(OLD_DEFAULT)}'"))
    op.drop_column("users", "reading_reminder_at")
