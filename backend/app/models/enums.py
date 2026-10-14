"""Python mirrors of the Postgres ENUM types.

The types themselves are created once, by the first migration. Models bind to
them with `create_type=False`, so SQLAlchemy never tries to (re)create them.
"""

import enum

from sqlalchemy.dialects.postgresql import ENUM


class UserRole(str, enum.Enum):
    user = "user"
    pending_phc = "pending_phc"
    phc_worker = "phc_worker"
    admin = "admin"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class BloodGroup(str, enum.Enum):
    a_pos = "A+"
    a_neg = "A-"
    b_pos = "B+"
    b_neg = "B-"
    ab_pos = "AB+"
    ab_neg = "AB-"
    o_pos = "O+"
    o_neg = "O-"


class Designation(str, enum.Enum):
    medical_officer = "medical_officer"
    staff_nurse = "staff_nurse"
    health_inspector = "health_inspector"
    asha_supervisor = "asha_supervisor"
    block_health_supervisor = "block_health_supervisor"


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PhcDocumentType(str, enum.Enum):
    employee_id_card = "employee_id_card"
    appointment_order = "appointment_order"
    registration_certificate = "registration_certificate"


class PhcDocumentStatus(str, enum.Enum):
    pending = "pending"
    auto_passed = "auto_passed"
    flagged = "flagged"
    rejected = "rejected"
    accepted = "accepted"


class PhcVerificationAction(str, enum.Enum):
    application_approved = "application_approved"
    application_rejected = "application_rejected"
    application_revoked = "application_revoked"
    document_accepted = "document_accepted"
    document_rejected = "document_rejected"


class AlertType(str, enum.Enum):
    personal = "personal"
    community = "community"


class AdvisoryScope(str, enum.Enum):
    centre = "centre"
    district = "district"
    state = "state"


class AlertSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class FlagResolution(str, enum.Enum):
    reviewed = "reviewed"
    dismissed = "dismissed"


class FlagDismissReason(str, enum.Enum):
    false_positive = "false_positive"
    already_treated = "already_treated"
    contacted = "contacted"
    other = "other"


class VisitStatus(str, enum.Enum):
    """Decisions only. "Overdue" is derived at read time (services/visit_state.py)."""

    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    missed = "missed"


class ConcernCategory(str, enum.Enum):
    data_misuse = "data_misuse"
    incorrect_diagnosis_flag = "incorrect_diagnosis_flag"
    harassment = "harassment"
    access_request = "access_request"
    other = "other"


class ConcernStatus(str, enum.Enum):
    open = "open"
    in_review = "in_review"
    resolved = "resolved"
    rejected = "rejected"


class ConsentType(str, enum.Enum):
    community_surveillance = "community_surveillance"
    health_tracking = "health_tracking"
    phc_worker_access = "phc_worker_access"
    research_analytics = "research_analytics"
    marketing_updates = "marketing_updates"


class ChatMessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class ChatRefusalReason(str, enum.Enum):
    insufficient_history = "insufficient_history"
    out_of_scope = "out_of_scope"
    no_matching_records = "no_matching_records"
    error = "error"


def pg_enum(enum_cls: type[enum.Enum], name: str) -> ENUM:
    """Bind a column to an existing Postgres ENUM, storing member *values*."""
    return ENUM(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda members: [m.value for m in members],
    )
