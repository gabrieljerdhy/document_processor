import io
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_and_text_flow():
    # Create a small fake pdf (just bytes); extractor may return empty, but pipeline should not crash
    fake_pdf = b"%PDF-1.1\n%EOF"  # minimal invalid pdf but okay for validation
    files = {"file": ("test.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    r = client.post("/documents/upload", files=files)
    assert r.status_code == 200
    doc_id = r.json()["document_id"]

    # Immediately fetching likely returns 409 while processing
    r2 = client.get(f"/documents/{doc_id}/text")
    assert r2.status_code in (200, 409, 404)

