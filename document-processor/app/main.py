from __future__ import annotations

import shutil
import sqlite3
import time
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.dependencies import get_queue_service
from .api.routes import router


class RateLimiter:
    def __init__(self, max_per_minute: int = 10) -> None:
        self.max = max_per_minute
        self.bucket: Dict[str, Dict[str, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        window = int(now // 60)
        entry = self.bucket.get(key)
        if not entry or entry["window"] != window:
            self.bucket[key] = {"window": window, "count": 1}
            return True
        if entry["count"] < self.max:
            entry["count"] += 1
            return True
        return False


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # start in-memory queue worker
    get_queue_service().start()
    try:
        yield
    finally:
        # gracefully stop worker
        await get_queue_service().stop()


app = FastAPI(title="Document Processing Service", lifespan=lifespan)
rl = RateLimiter(max_per_minute=10)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "anon"
    if not rl.allow(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return await call_next(request)


# Global catch-all exception handler: detailed in dev, sanitized in prod
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import os

    if os.getenv("APP_ENV", "dev").lower().startswith("prod"):
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
async def health():
    # DB check
    db_status = "ok"
    try:
        import os

        from .database import DB_PATH

        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1;")
        conn.close()
    except Exception:
        db_status = "failed"

    # Library checks
    try:
        import pdfplumber  # type: ignore

        has_pdfplumber = True
    except Exception:
        has_pdfplumber = False
    try:
        from pypdf import PdfReader  # type: ignore

        has_pypdf = True
    except Exception:
        has_pypdf = False
    try:
        import pypdfium2 as pdfium  # type: ignore

        has_pdfium = True
    except Exception:
        has_pdfium = False
    try:
        import pytesseract  # type: ignore

        has_pytesseract = True
        try:
            _ = pytesseract.get_tesseract_version()
            tesseract_bin = "ok"
        except Exception:
            tesseract_bin = "missing"
    except Exception:
        has_pytesseract = False
        tesseract_bin = "missing"

    overall = "ok"
    if db_status != "ok":
        overall = "failed"
    elif not (has_pdfplumber or has_pypdf):
        overall = "degraded"

    return {
        "status": overall,
        "dependencies": {
            "db": db_status,
            "pdfplumber": "ok" if has_pdfplumber else "missing",
            "pypdf": "ok" if has_pypdf else "missing",
            "pypdfium2": "ok" if has_pdfium else "missing",
            "pytesseract": "ok" if has_pytesseract else "missing",
            "tesseract_binary": tesseract_bin,
        },
    }


app.include_router(router)
