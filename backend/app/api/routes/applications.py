"""Verification documents: the applicant uploads them, an admin reads and decides on them."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_session
from app.models import AuditLog, PhcApplication, PhcVerificationAuditLog, PhcVerificationDocument, User
from app.models.base import utcnow
from app.models.enums import ApplicationStatus, PhcDocumentStatus, PhcDocumentType, PhcVerificationAction, UserRole
from app.services import documents, sessions

router = APIRouter(prefix="/phc-application", tags=["phc application"])
admin_router = APIRouter(prefix="/admin/applications", tags=["admin"], dependencies=[Depends(require_admin)])

MAX_DOCUMENTS = 6
NOT_FOUND = "Document not found."


class DocumentOut(BaseModel):
    id: uuid.UUID
    document_type: PhcDocumentType
    original_filename: str | None
    content_type: str
    size_bytes: int
    status: PhcDocumentStatus
    check_notes: str | None
    extracted_registration_no: str | None
    tamper_score: int | None
    uploaded_at: datetime
    checked_at: datetime | None


class Decision(BaseModel):
    accept: bool
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


def document_out(d: PhcVerificationDocument) -> DocumentOut:
    return DocumentOut(
        id=d.id, document_type=d.document_type, original_filename=d.original_filename, content_type=d.content_type,
        size_bytes=d.size_bytes, status=d.status, check_notes=d.check_notes,
        extracted_registration_no=d.extracted_registration_no, tamper_score=d.tamper_score,
        uploaded_at=d.uploaded_at, checked_at=d.checked_at,
    )


async def documents_of(db: AsyncSession, application_id: uuid.UUID) -> list[DocumentOut]:
    rows = await db.scalars(
        select(PhcVerificationDocument)
        .where(PhcVerificationDocument.application_id == application_id, PhcVerificationDocument.deleted_at.is_(None))
        .order_by(PhcVerificationDocument.uploaded_at)
    )
    return [document_out(d) for d in rows]


async def applicant(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> tuple[User, PhcApplication]:
    if user.role != UserRole.pending_phc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Documents are for PHC worker applications awaiting review.")
    application = await db.scalar(select(PhcApplication).where(PhcApplication.user_id == user.id))
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No application found.")
    return user, application


@router.get("/documents", response_model=list[DocumentOut])
async def my_documents(who=Depends(applicant), db: AsyncSession = Depends(get_session)) -> list[DocumentOut]:
    return await documents_of(db, who[1].id)


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload(
    document_type: PhcDocumentType = Form(...),
    file: UploadFile = File(...),
    who=Depends(applicant),
    db: AsyncSession = Depends(get_session),
) -> DocumentOut:
    user, application = who
    if application.status != ApplicationStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "This application has already been decided.")
    count = await db.scalar(
        select(func.count()).where(
            PhcVerificationDocument.application_id == application.id, PhcVerificationDocument.deleted_at.is_(None)
        )
    )
    if (count or 0) >= MAX_DOCUMENTS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"At most {MAX_DOCUMENTS} documents. Remove one first.")
    data = await file.read(documents.MAX_BYTES + 1)
    if len(data) > documents.MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Files can be up to 5 MB.")
    kind = documents.sniff(data[:8])
    if kind is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a JPEG, PNG or PDF.")
    content_type, ext = kind

    doc = PhcVerificationDocument(
        application_id=application.id,
        user_id=user.id,
        document_type=document_type,
        storage_key=documents.store(data, ext),
        content_type=content_type,
        size_bytes=len(data),
        sha256=documents.digest(data),
        original_filename=(file.filename or "")[:200] or None,
    )
    findings = await documents.check(db, doc, data, application, user)
    doc.status = findings.status
    doc.check_notes = " ".join(findings.notes) or None
    doc.ocr_text = findings.ocr_text
    doc.extracted_registration_no = findings.registration_no
    doc.tamper_score = findings.tamper_score
    doc.checked_at = utcnow()
    db.add(doc)
    await db.commit()
    return document_out(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(document_id: uuid.UUID, who=Depends(applicant), db: AsyncSession = Depends(get_session)) -> None:
    user, application = who
    doc = await db.get(PhcVerificationDocument, document_id)
    if doc is None or doc.user_id != user.id or doc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if application.status != ApplicationStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "This application has already been decided.")
    doc.deleted_at = utcnow()
    await db.commit()


async def _admin_doc(db: AsyncSession, application_id: uuid.UUID, document_id: uuid.UUID) -> PhcVerificationDocument:
    doc = await db.get(PhcVerificationDocument, document_id)
    if doc is None or doc.application_id != application_id or doc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return doc


@admin_router.get("/{application_id}/documents/{document_id}/file")
async def view_file(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> FileResponse:
    doc = await _admin_doc(db, application_id, document_id)
    path = documents.path_of(doc.storage_key)
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "The file is no longer stored.")
    db.add(AuditLog(user_id=admin.id, action="view_verification_document", entity="phc_verification_documents",
                    entity_id=doc.id, ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    return FileResponse(path, media_type=doc.content_type, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@admin_router.post("/{application_id}/documents/{document_id}/decision", response_model=DocumentOut)
async def decide(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    data: Decision,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> DocumentOut:
    doc = await _admin_doc(db, application_id, document_id)
    if not data.accept and not data.reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Say why the document is rejected.")
    application = await db.get(PhcApplication, application_id)
    before = doc.status.value
    doc.status = PhcDocumentStatus.accepted if data.accept else PhcDocumentStatus.rejected
    db.add(PhcVerificationAuditLog(
        application_id=application_id,
        subject_user_id=application.user_id,
        actor_user_id=admin.id,
        action=PhcVerificationAction.document_accepted if data.accept else PhcVerificationAction.document_rejected,
        from_status=before,
        to_status=doc.status.value,
        reason=data.reason or f"{doc.document_type.value.replace('_', ' ')}",
        ip_address=sessions.client_ip(request) or "unknown",
    ))
    await db.commit()
    return document_out(doc)
