"""Every model is imported here so Base.metadata (and Alembic) sees all tables."""

from .alert import Alert
from .audit_log import AuditLog
from .base import Base
from .chat_message import ChatMessage
from .chat_session import ChatSession
from .community_data import CommunityData
from .concern import Concern
from .consent_record import ConsentRecord
from .health_record import HealthRecord
from .phc_application import PhcApplication
from .phc_verification_audit_log import PhcVerificationAuditLog
from .phc_verification_document import PhcVerificationDocument
from .processed_data import ProcessedData
from .refresh_token import RefreshToken
from .scheduled_visit import ScheduledVisit
from .user import User
from .user_profile import UserProfile
from .valid_phc_facility import ValidPhcFacility

__all__ = [
    "Alert",
    "AuditLog",
    "Base",
    "ChatMessage",
    "ChatSession",
    "CommunityData",
    "Concern",
    "ConsentRecord",
    "HealthRecord",
    "PhcApplication",
    "PhcVerificationAuditLog",
    "PhcVerificationDocument",
    "ProcessedData",
    "RefreshToken",
    "ScheduledVisit",
    "User",
    "UserProfile",
    "ValidPhcFacility",
]
