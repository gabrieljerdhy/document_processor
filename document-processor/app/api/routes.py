from __future__ import annotations

import time
from typing import Any, Dict, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..api.dependencies import (
    get_ocr_service,
    get_parser_service,
    get_queue_service,
    get_repo,
)
from ..database import DocumentRepository
from ..models import ParsedData
from ..services.ocr_service import OCRService
from ..services.parser_service import ParserService
from ..services.queue_service import InMemoryQueueService
from ..utils.validators import validate_file

# Simple in-memory cache for extracted text with TTL (seconds)
TEXT_CACHE: Dict[str, Tuple[str, float]] = {}

router = APIRouter()


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    repo: DocumentRepository = Depends(get_repo),
    queue: InMemoryQueueService = Depends(get_queue_service),
) -> Dict[str, Any]:
    try:
        ext, size = validate_file(file)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    content = await file.read()
    meta = repo.create_document(file.filename or "file", ext, size)
    document_id = meta["id"]

    # Ensure worker is running and enqueue for background processing
    queue.start()
    queue.enqueue(document_id, ext, content)
    return {"document_id": document_id, "status": meta["status"]}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str, repo: DocumentRepository = Depends(get_repo)
) -> Dict[str, Any]:
    doc = repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # sanitize
    return {
        "document_id": doc["id"],
        "file_name": doc["file_name"],
        "file_type": doc["file_type"],
        "file_size": doc["file_size"],
        "status": doc["status"],
        "raw_text": doc.get("raw_text") or "",
        "parsed_data": doc.get("parsed_data") or None,
        "error_message": doc.get("error_message"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


@router.get("/documents/{document_id}/text")
async def get_document_text(
    document_id: str,
    format: Optional[Literal["plain", "json", "markdown"]] = "plain",
    repo: DocumentRepository = Depends(get_repo),
):
    doc = repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["status"] != "completed":
        raise HTTPException(
            status_code=409, detail=f"Document status is {doc['status']}"
        )

    # Cache lookup and set (1 hour TTL)
    now = time.time()
    cached = TEXT_CACHE.get(document_id)
    if cached and cached[1] > now:
        text = cached[0]
    else:
        text = (doc.get("raw_text") or "").strip()
        TEXT_CACHE[document_id] = (text, now + 3600)

    if format == "json":
        return {"document_id": document_id, "text": text}
    if format == "markdown":
        return f"# Document {document_id}\n\n````\n{text}\n````"
    return text


@router.post("/documents/{document_id}/parse")
async def parse_document(
    document_id: str,
    parser_type: Literal["invoice", "receipt", "contract"],
    repo: DocumentRepository = Depends(get_repo),
    parser: ParserService = Depends(get_parser_service),
) -> ParsedData:
    doc = repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["status"] != "completed":
        raise HTTPException(
            status_code=409, detail=f"Document status is {doc['status']}"
        )
    text = doc.get("raw_text") or ""
    parsed = parser.parse(parser_type, text)
    repo.update_status(document_id, doc["status"], parsed_data=parsed.model_dump())
    return parsed
