"""Work for the admin console: pending worker applications with documents, open concerns and an advisory.

    python -m app.seeds.seed_admin_workflow

Run after seed_directory and seed_citizen. Applicants share DEMO_CITIZEN_PASSWORD (or a
generated one, printed). Idempotent: applicants and concerns that exist are left alone.
"""

import io
from datetime import timedelta

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Advisory, Concern, PhcApplication, PhcVerificationDocument, User, ValidPhcFacility
from app.models.enums import (
    AdvisoryScope,
    AlertSeverity,
    ConcernCategory,
    ConcernStatus,
    Designation,
    PhcDocumentType,
    UserRole,
)
from app.services import documents

from ._common import password_or_generated, run, user_by_email, utcnow

APPLICANTS = [
    ("Lakshmi Narayanan", "lakshmi.applicant@example.com", "TNPHC-CHN-4410", Designation.staff_nurse, "Mylapore PHC", "card"),
    ("Arun Prakash", "arun.applicant@example.com", "TNPHC-CHN-4411", Designation.health_inspector, "Adyar PHC", "copy"),
    ("Deepa Selvam", "deepa.applicant@example.com", "TNPHC-CHN-4412", Designation.asha_supervisor, "Royapettah Primary Health Centre", None),
]

CONCERNS = [
    (ConcernCategory.incorrect_diagnosis_flag, ConcernStatus.open,
     "My blood pressure reading from Tuesday evening was flagged, but I had just climbed the stairs. Please review it."),
    (ConcernCategory.access_request, ConcernStatus.in_review,
     "I would like a copy of all the readings my health worker recorded during home visits."),
    (ConcernCategory.other, ConcernStatus.open,
     "My smartwatch sync showed the same reading twice this morning. Is that expected?"),
]


def id_card(name: str, employee_id: str, facility: str) -> bytes:
    img = Image.new("RGB", (1000, 640), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 1000, 110], fill=(20, 90, 70))
    draw.text((40, 40), "GOVERNMENT OF TAMIL NADU - HEALTH DEPARTMENT", fill="white")
    for i, line in enumerate([f"Name: {name}", f"Employee No: {employee_id}", f"Posting: {facility}", "Valid till: 2028"]):
        draw.text((60, 180 + i * 70), line, fill="black")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


async def seed(session: AsyncSession) -> None:
    password = password_or_generated(get_settings().DEMO_CITIZEN_PASSWORD, "Demo applicants")
    hashed = hash_password(password)
    now = utcnow()
    shared_file: bytes | None = None

    for name, email, employee_id, designation, phc_name, docs in APPLICANTS:
        if await user_by_email(session, email):
            continue
        user = User(name=name, email=email, hashed_password=hashed, role=UserRole.pending_phc, is_verified=True,
                    email_verified=True, verified_at=now, consent=True, district="Chennai", state="Tamil Nadu")
        session.add(user)
        await session.flush()
        application = PhcApplication(user_id=user.id, employee_id=employee_id, designation=designation, phc_name=phc_name,
                                     district="Chennai", state="Tamil Nadu", years_of_service=6)
        session.add(application)
        await session.flush()
        if docs is None:
            continue
        data = id_card(name, employee_id, phc_name) if docs == "card" else shared_file
        if docs == "card":
            shared_file = data
        doc = PhcVerificationDocument(
            application_id=application.id, user_id=user.id, document_type=PhcDocumentType.employee_id_card,
            storage_key=documents.store(data, ".png"), content_type="image/png", size_bytes=len(data),
            sha256=documents.digest(data), original_filename="employee-id.png",
        )
        session.add(doc)
        await session.flush()
        findings = await documents.check(session, doc, data, application, user)
        doc.status, doc.check_notes, doc.ocr_text = findings.status, " ".join(findings.notes), findings.ocr_text
        doc.extracted_registration_no, doc.tamper_score, doc.checked_at = findings.registration_no, findings.tamper_score, now

    citizen = await user_by_email(session, "citizen.demo@example.com")
    if citizen and not await session.scalar(select(Concern.id).where(Concern.user_id == citizen.id).limit(1)):
        for i, (category, state, text) in enumerate(CONCERNS):
            session.add(Concern(user_id=citizen.id, category=category, status=state, description=text,
                                created_at=now - timedelta(days=3 - i)))

    admin = await user_by_email(session, "admin.chennai@admin.example.com")
    if admin and not await session.scalar(select(Advisory.id).where(Advisory.author_id == admin.id).limit(1)):
        session.add(Advisory(
            author_id=admin.id, scope=AdvisoryScope.district, district="Chennai", state="Tamil Nadu",
            title="Monsoon fever precautions",
            body="Fever cases usually rise with the monsoon. Empty standing water around your home every week, and see "
                 "your health centre if a fever lasts more than two days.",
            severity=AlertSeverity.medium, expires_at=now + timedelta(days=21),
        ))

    mylapore = await session.scalar(select(ValidPhcFacility).where(ValidPhcFacility.name == "Mylapore PHC"))
    print(f"Pending applicants: {len(APPLICANTS)} (password {password}). Concerns and an advisory added. "
          f"Mylapore PHC found: {mylapore is not None}.")


if __name__ == "__main__":
    run(seed)
