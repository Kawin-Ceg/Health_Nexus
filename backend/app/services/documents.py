"""PHC worker verification documents: private storage and the automatic checks.

Files go to PRIVATE_UPLOAD_DIR under random names and are only ever served to admins.
The checks never approve anyone; they sort documents for the admin:

- the same file already sent with another person's application -> flagged
- saved by an image editor (EXIF Software tag) -> flagged
- OCR (Tesseract, when installed) finds the employee ID and the applicant's name -> auto_passed
- OCR ran but found neither -> flagged
- anything else, including PDFs and no Tesseract -> pending, for manual review
"""

import asyncio
import hashlib
import io
import re
import secrets
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import PhcApplication, PhcVerificationDocument, User
from app.models.enums import PhcDocumentStatus

MAX_BYTES = 5 * 1024 * 1024
TYPES = {b"\xff\xd8\xff": ("image/jpeg", ".jpg"), b"\x89PNG\r\n\x1a\n": ("image/png", ".png"), b"%PDF-": ("application/pdf", ".pdf")}
EDITORS = ("photoshop", "gimp", "canva", "picsart", "snapseed", "lightroom", "pixlr", "paint.net", "affinity")
MIN_SIDE = 600


def private_root() -> Path:
    return Path(get_settings().PRIVATE_UPLOAD_DIR).resolve()


def sniff(head: bytes) -> tuple[str, str] | None:
    for magic, kind in TYPES.items():
        if head.startswith(magic):
            return kind
    return None


def store(data: bytes, ext: str) -> str:
    key = f"{secrets.token_hex(16)}{ext}"
    root = private_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / key).write_bytes(data)
    return key


def path_of(key: str) -> Path:
    path = (private_root() / key).resolve()
    if path.parent != private_root():
        raise ValueError("Bad storage key")
    return path


def tesseract_available() -> bool:
    try:
        import pytesseract
    except ImportError:
        return False
    if get_settings().TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = get_settings().TESSERACT_CMD
    return shutil.which(pytesseract.pytesseract.tesseract_cmd) is not None or Path(pytesseract.pytesseract.tesseract_cmd).exists()


def read_text(data: bytes) -> str | None:
    """OCR text of an image, or None when OCR cannot run."""
    if not tesseract_available():
        return None
    import pytesseract
    from PIL import Image, ImageOps

    image = ImageOps.grayscale(Image.open(io.BytesIO(data)))
    if min(image.size) < 1200:
        scale = 1200 / min(image.size)
        image = image.resize((round(image.width * scale), round(image.height * scale)))
    return pytesseract.image_to_string(image)


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


@dataclass
class Findings:
    status: PhcDocumentStatus
    notes: list[str] = field(default_factory=list)
    ocr_text: str | None = None
    registration_no: str | None = None
    tamper_score: int = 0


def inspect_image(data: bytes) -> tuple[list[str], int]:
    from PIL import Image

    notes, score = [], 0
    try:
        image = Image.open(io.BytesIO(data))
        software = str(image.getexif().get(0x0131, "")).lower()
        if any(name in software for name in EDITORS):
            notes.append(f"Saved by an image editor ({software.strip()}).")
            score += 60
        if min(image.size) < MIN_SIDE:
            notes.append(f"Low resolution ({image.width}x{image.height}); may be hard to read.")
            score += 10
    except Exception:
        notes.append("The image could not be opened.")
        score += 40
    return notes, score


def judge(data: bytes, content_type: str, application: PhcApplication, applicant: User, duplicate_of_other: bool,
          ocr: str | None) -> Findings:
    findings = Findings(PhcDocumentStatus.pending, ocr_text=ocr)
    if duplicate_of_other:
        findings.notes.append("The same file was sent with another person's application.")
        findings.tamper_score += 80
    if content_type != "application/pdf":
        notes, score = inspect_image(data)
        findings.notes += notes
        findings.tamper_score += score

    if ocr is None:
        findings.notes.append(
            "Text not checked: PDF files are reviewed by hand." if content_type == "application/pdf"
            else "Text not checked: OCR (Tesseract) is not installed on the server."
        )
    else:
        text = _squash(ocr)
        id_found = bool(application.employee_id) and _squash(application.employee_id) in text
        name_parts = [p for p in re.split(r"\s+", applicant.name.lower()) if len(p) > 2]
        name_found = bool(name_parts) and all(_squash(p) in text for p in name_parts)
        facility_found = _squash(application.phc_name)[:12] in text if application.phc_name else False
        if id_found:
            findings.registration_no = application.employee_id
        findings.notes.append(
            "Found: " + ", ".join(k for k, ok in (("employee ID", id_found), ("name", name_found), ("health centre", facility_found)) if ok)
            if id_found or name_found or facility_found else "Neither the employee ID nor the name was found in the text."
        )
        if id_found and name_found and findings.tamper_score < 50:
            findings.status = PhcDocumentStatus.auto_passed
        elif not (id_found or name_found):
            findings.status = PhcDocumentStatus.flagged

    if findings.tamper_score >= 50:
        findings.status = PhcDocumentStatus.flagged
    findings.tamper_score = min(findings.tamper_score, 100)
    return findings


async def check(session: AsyncSession, doc: PhcVerificationDocument, data: bytes, application: PhcApplication,
                applicant: User) -> Findings:
    duplicate = await session.scalar(
        select(PhcVerificationDocument.id).where(
            PhcVerificationDocument.sha256 == doc.sha256,
            PhcVerificationDocument.user_id != doc.user_id,
            PhcVerificationDocument.deleted_at.is_(None),
        ).limit(1)
    )
    ocr = None
    if doc.content_type != "application/pdf":
        try:
            ocr = await asyncio.to_thread(read_text, data)
        except Exception:
            ocr = None
    return judge(data, doc.content_type, application, applicant, duplicate is not None, ocr)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
