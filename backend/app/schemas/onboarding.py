import re
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, model_validator

from app.models.enums import BloodGroup, Gender

MAX_TAGS = 10


def _blank_to_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


def _check_phone(value: str) -> str:
    if not re.fullmatch(r"\+?[0-9]{7,15}", re.sub(r"[\s\-()]", "", value)):
        raise ValueError("Enter a valid phone number")
    return value


def _dedupe(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for tag in tags:
        if tag.casefold() not in seen:
            seen.add(tag.casefold())
            unique.append(tag)
    return unique


Age = Annotated[int, Field(ge=1, le=120)]
HeightCm = Annotated[float, Field(ge=50, le=300)]
WeightKg = Annotated[float, Field(ge=1, le=300)]
Place = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Pincode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{6}$")]
Area = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Tags = Annotated[list[Tag], Field(max_length=MAX_TAGS), AfterValidator(_dedupe)]
# Constraints sit on the inner str: applied to `str | None` they would run on None.
OptionalText = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None, BeforeValidator(_blank_to_none)
]
OptionalPhone = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=25), AfterValidator(_check_phone)] | None,
    BeforeValidator(_blank_to_none),
]


class ProfileFields(BaseModel):
    """Everything onboarding collects except the consent answers. Also the target
    that a PATCH is merged into and re-validated against."""

    # Step 1
    age: Age
    gender: Gender
    height_cm: HeightCm
    weight_kg: WeightKg
    blood_group: BloodGroup | None = None
    # Step 2. The facility is chosen, and must serve the district given.
    state: Place
    district: Place
    phc_id: uuid.UUID
    pincode: Pincode
    area: Area
    # Step 3
    existing_conditions: Tags = []
    current_medications: Tags = []
    # Step 4
    has_smartwatch: bool = False
    smartwatch_brand: OptionalText = None
    emergency_contact_name: OptionalText = None
    emergency_contact_phone: OptionalPhone = None

    @model_validator(mode="after")
    def _cross_field(self) -> "ProfileFields":
        if self.smartwatch_brand and not self.has_smartwatch:
            raise ValueError("A smartwatch brand needs has_smartwatch to be true")
        if self.emergency_contact_name and not self.emergency_contact_phone:
            raise ValueError("An emergency contact name needs a phone number")
        if self.emergency_contact_phone and not self.emergency_contact_name:
            raise ValueError("An emergency contact phone number needs a name")
        return self


class ConsentAnswers(BaseModel):
    """Step 5. The answers are explicit; there is no default to fall back on.

    phc_worker_access is optional for older clients: unanswered, a citizen's centre
    can see them until they turn it off (services/consent.allows_worker_access).
    """

    health_tracking: bool
    community_surveillance: bool
    phc_worker_access: bool | None = None


class ProfileCreate(ProfileFields):
    consents: ConsentAnswers


class ProfilePatch(BaseModel):
    """Any subset of ProfileFields. Consent changes go through PATCH /auth/consent."""

    model_config = ConfigDict(extra="forbid")

    age: Age | None = None
    gender: Gender | None = None
    height_cm: HeightCm | None = None
    weight_kg: WeightKg | None = None
    blood_group: BloodGroup | None = None
    state: Place | None = None
    district: Place | None = None
    phc_id: uuid.UUID | None = None
    pincode: Pincode | None = None
    area: Area | None = None
    existing_conditions: Tags | None = None
    current_medications: Tags | None = None
    has_smartwatch: bool | None = None
    smartwatch_brand: OptionalText = None
    emergency_contact_name: OptionalText = None
    emergency_contact_phone: OptionalPhone = None


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    block: str | None
    district: str
    state: str


class FacilityOption(FacilityOut):
    """A centre as offered during onboarding: how many workers review readings there."""

    workers_assigned: int = 0


class ProfileOut(BaseModel):
    age: int
    gender: Gender
    height_cm: float
    weight_kg: float
    blood_group: BloodGroup | None
    state: str | None
    district: str | None
    phc_id: uuid.UUID | None
    facility: FacilityOut | None
    pincode: str | None
    area: str | None
    existing_conditions: list[str]
    current_medications: list[str]
    has_smartwatch: bool
    smartwatch_brand: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    consents: ConsentAnswers | None
