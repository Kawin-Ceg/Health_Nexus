import io

import pytest
from PIL import Image

from app.core.config import get_settings
from app.models.enums import UserRole
from app.services import documents

from .conftest import BASE, PASSWORD, register_and_login
from .test_admin import PHC_SIGNUP
from .test_modules import make_user


@pytest.fixture(autouse=True)
def private_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "PRIVATE_UPLOAD_DIR", str(tmp_path))


@pytest.fixture
def ocr(monkeypatch):
    text = {"value": None}
    monkeypatch.setattr(documents, "read_text", lambda data: text["value"])
    return text


def image(fmt="PNG", software=None, size=(1000, 700), colour="white") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, colour)
    if software:
        exif = img.getexif()
        exif[0x0131] = software
        img.save(buf, fmt, exif=exif)
    else:
        img.save(buf, fmt)
    return buf.getvalue()


async def applicant(client, outbox, email="meena@example.com", employee_id="TNPHC-CHN-2847"):
    body = {**PHC_SIGNUP, "email": email, "employee_id": employee_id}
    assert (await client.post(f"{BASE}/auth/register/phc-worker", json=body)).status_code == 201
    token = outbox.verification[-1][1]
    await client.post(f"{BASE}/auth/email/verify", json={"token": token})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def upload(client, headers, data, kind="employee_id_card", name="card.png"):
    return await client.post(
        f"{BASE}/phc-application/documents", data={"document_type": kind}, files={"file": (name, data)}, headers=headers
    )


async def test_ocr_that_finds_the_id_and_name_passes(client, outbox, ocr):
    wh = await applicant(client, outbox)
    ocr["value"] = "GOVERNMENT OF TAMIL NADU\nMeena S\nStaff Nurse\nEmp No: TNPHC CHN 2847"
    r = await upload(client, wh, image())
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["status"] == "auto_passed" and doc["extracted_registration_no"] == "TNPHC-CHN-2847"
    assert "employee ID" in doc["check_notes"] and "name" in doc["check_notes"]


async def test_without_ocr_a_document_waits_for_a_person(client, outbox, ocr):
    wh = await applicant(client, outbox)
    doc = (await upload(client, wh, image())).json()
    assert doc["status"] == "pending" and "not installed" in doc["check_notes"]
    pdf = (await upload(client, wh, b"%PDF-1.4\n...", kind="appointment_order", name="order.pdf")).json()
    assert pdf["status"] == "pending" and "PDF" in pdf["check_notes"]


async def test_edited_and_reused_files_are_flagged(client, outbox, ocr):
    wh = await applicant(client, outbox)
    edited = (await upload(client, wh, image("JPEG", software="Adobe Photoshop 25.0"), name="card.jpg")).json()
    assert edited["status"] == "flagged" and "image editor" in edited["check_notes"]

    shared = image(colour="ivory")
    assert (await upload(client, wh, shared)).json()["status"] == "pending"
    other = await applicant(client, outbox, email="ravi.n@example.com", employee_id="TNPHC-CHN-9999")
    copied = (await upload(client, other, shared)).json()
    assert copied["status"] == "flagged" and "another person's application" in copied["check_notes"]


async def test_bad_files_are_refused(client, outbox, ocr):
    wh = await applicant(client, outbox)
    assert (await upload(client, wh, b"MZ\x90\x00 not an image", name="x.exe")).status_code == 415
    assert (await upload(client, wh, b"\x89PNG\r\n\x1a\n" + b"0" * (documents.MAX_BYTES + 1))).status_code == 413


async def test_admin_reviews_documents(client, outbox, db, ocr):
    wh = await applicant(client, outbox)
    data = image()
    doc = (await upload(client, wh, data)).json()
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    app_id = (await client.get(f"{BASE}/admin/applications?status=pending", headers=ah)).json()["items"][0]["id"]
    detail = (await client.get(f"{BASE}/admin/applications/{app_id}", headers=ah)).json()
    assert [d["id"] for d in detail["documents"]] == [doc["id"]]

    file = await client.get(f"{BASE}/admin/applications/{app_id}/documents/{doc['id']}/file", headers=ah)
    assert file.status_code == 200 and file.content == data
    assert (await client.get(f"{BASE}/admin/applications/{app_id}/documents/{doc['id']}/file", headers=wh)).status_code == 403

    url = f"{BASE}/admin/applications/{app_id}/documents/{doc['id']}/decision"
    assert (await client.post(url, json={"accept": False}, headers=ah)).status_code == 422
    assert (await client.post(url, json={"accept": True}, headers=ah)).json()["status"] == "accepted"
    history = (await client.get(f"{BASE}/admin/applications/{app_id}", headers=ah)).json()["history"]
    assert history[0]["action"] == "document_accepted"

    assert (await client.delete(f"{BASE}/phc-application/documents/{doc['id']}", headers=wh)).status_code == 204
    assert (await client.get(f"{BASE}/phc-application/documents", headers=wh)).json() == []


async def test_only_applicants_upload(client, outbox):
    citizen = await register_and_login(client, outbox)
    assert (await upload(client, citizen, image())).status_code == 403
