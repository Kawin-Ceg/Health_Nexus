import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.patterns import EMPLOYEE_ID_PATTERN, is_valid_employee_id
from app.models.enums import ApplicationStatus, ConsentType, Designation, UserRole

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not _EMAIL_RE.fullmatch(value):
        raise ValueError("Enter a valid email address")
    return value


def _check_password(value: str) -> str:
    # bcrypt reads only the first 72 bytes; refuse rather than silently truncate.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return value


def _check_employee_id(value: str) -> str:
    if not is_valid_employee_id(value):
        raise ValueError(f"Employee ID must match {EMPLOYEE_ID_PATTERN} (for example TNPHC-CHN-2847)")
    return value


Email = Annotated[str, AfterValidator(_clean_email)]
Password = Annotated[str, Field(min_length=8), AfterValidator(_check_password)]
Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class CitizenRegister(BaseModel):
    name: Text100
    email: Email
    password: Password


class PhcWorkerRegister(CitizenRegister):
    employee_id: Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_check_employee_id)]
    designation: Designation
    phc_name: Text100
    district: Text100
    state: Text100
    years_of_service: Annotated[int, Field(ge=0, le=60)]


class LoginRequest(BaseModel):
    # Deliberately unvalidated beyond presence: a malformed address gets the
    # same answer as an unknown one.
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=254)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class TokenRequest(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=256)]


class ForgotPasswordRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=254)]


class ResetPasswordRequest(TokenRequest):
    new_password: Password


class ConsentChoice(BaseModel):
    consent_type: ConsentType
    granted: bool


class ConsentUpdate(BaseModel):
    consents: Annotated[list[ConsentChoice], Field(min_length=1, max_length=len(ConsentType))]

    @model_validator(mode="after")
    def _unique_types(self) -> "ConsentUpdate":
        types = [c.consent_type for c in self.consents]
        if len(set(types)) != len(types):
            raise ValueError("Each consent type may appear once")
        return self


class ConsentState(BaseModel):
    consents: dict[ConsentType, bool]


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    designation: Designation
    phc_name: str
    district: str
    state: str
    years_of_service: int
    status: ApplicationStatus
    rejection_reason: str | None = None
    created_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_verified: bool
    profile_completed: bool
    consent: bool
    phc_id: uuid.UUID | None
    state: str | None
    district: str | None
    created_at: datetime
    # Only for pending_phc: what they applied with.
    application: ApplicationOut | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class SessionOut(BaseModel):
    id: uuid.UUID
    device_label: str | None
    ip_address: str | None
    created_at: datetime
    last_activity_at: datetime
    is_current: bool


class Message(BaseModel):
    detail: str
