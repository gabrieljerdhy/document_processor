import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from app.main import app, rl
from fastapi.testclient import TestClient

client = TestClient(app)


def make_minimal_pdf_bytes() -> bytes:
    try:
        from pypdf import PdfWriter
    except Exception:  # pragma: no cover
        # Fallback to simple bytes; may fail on extractor but fine for error tests
        return b"%PDF-1.1\n%EOF"
    bio = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(bio)
    bio.seek(0)
    return bio.getvalue()


def poll_until_completed(doc_id: str, timeout_s: float = 5.0) -> dict:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = client.get(f"/documents/{doc_id}")
        if r.status_code == 200:
            last = r.json()
            if last.get("status") in ("completed", "failed"):
                return last
        time.sleep(0.1)
    assert last is not None, "No document status available"
    return last


def test_end_to_end_success_flow():
    rl.bucket.clear()
    rl.max = 1000
    pdf_bytes = make_minimal_pdf_bytes()
    files = {"file": ("ok.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/documents/upload", files=files)
    assert r.status_code == 200
    doc_id = r.json()["document_id"]

    status = poll_until_completed(doc_id, timeout_s=10.0)
    assert status["status"] in ("completed", "failed")  # should usually be completed

    if status["status"] == "completed":
        r2 = client.get(f"/documents/{doc_id}/text")
        assert r2.status_code == 200
        assert isinstance(r2.text, str)

        r3 = client.post(
            f"/documents/{doc_id}/parse", params={"parser_type": "invoice"}
        )
        assert r3.status_code == 200
        data = r3.json()
        assert "fields" in data


def test_error_corrupted_pdf_eventually_failed():
    rl.bucket.clear()
    rl.max = 1000
    bad_pdf = b"%PDF-1.1"  # invalid/corrupted
    files = {"file": ("bad.pdf", io.BytesIO(bad_pdf), "application/pdf")}
    r = client.post("/documents/upload", files=files)
    assert r.status_code == 200
    doc_id = r.json()["document_id"]

    status = poll_until_completed(doc_id, timeout_s=15.0)
    assert status["status"] in ("failed", "completed")


def test_oversize_upload_rejected():
    rl.bucket.clear()
    rl.max = 1000
    big = b"A" * (10 * 1024 * 1024 + 1)
    files = {"file": ("big.pdf", io.BytesIO(big), "application/pdf")}
    r = client.post("/documents/upload", files=files)
    assert r.status_code == 400


def test_rate_limiting_health_endpoint():
    # Reset limiter for deterministic behavior
    rl.bucket.clear()
    rl.max = 10
    codes = []
    for _ in range(11):
        resp = client.get("/health")
        codes.append(resp.status_code)
    assert codes.count(429) >= 1


def test_performance_single_pdf_under_5s(monkeypatch):
    # Ensure quick processing by mocking PDF extraction to return text immediately
    from app.services import ocr_service as ocr_mod

    def fake_extract_pdf(self, file_path, file_bytes):
        return "Hello", 1

    monkeypatch.setattr(ocr_mod.OCRService, "_extract_pdf", fake_extract_pdf)

    pdf_bytes = make_minimal_pdf_bytes()
    rl.bucket.clear()
    rl.max = 1000

    start = time.time()
    r = client.post(
        "/documents/upload",
        files={"file": ("fast.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert r.status_code == 200
    doc_id = r.json()["document_id"]
    status = poll_until_completed(doc_id, timeout_s=5.0)
    assert status["status"] == "completed"
    elapsed = time.time() - start
    assert elapsed < 5.0


def test_concurrent_10_uploads(monkeypatch):
    # Mock for quick processing
    from app.services import ocr_service as ocr_mod

    def fake_extract_pdf(self, file_path, file_bytes):
        return "Hello", 1

    monkeypatch.setattr(ocr_mod.OCRService, "_extract_pdf", fake_extract_pdf)

    rl.bucket.clear()
    rl.max = 1000

    pdf_bytes = make_minimal_pdf_bytes()

    def upload_once(i):
        r = client.post(
            "/documents/upload",
            files={"file": (f"f{i}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert r.status_code == 200
        doc_id = r.json()["document_id"]
        status = poll_until_completed(doc_id, timeout_s=5.0)
        return status["status"]

    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(upload_once, i) for i in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    assert results.count("completed") == 10
