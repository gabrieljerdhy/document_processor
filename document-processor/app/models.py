from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    file_name: str
    file_type: Literal["pdf", "png", "jpg", "docx"]
    file_size: int
    uploaded_by: Optional[str] = "system"


class DocumentStatus(BaseModel):
    document_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class ExtractedContent(BaseModel):
    document_id: str
    raw_text: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    pages: Optional[int] = None
    language: Optional[str] = "en"


class ParsedData(BaseModel):
    document_type: str
    fields: Dict[str, Any]
    validation_errors: List[str] = Field(default_factory=list)
    parsing_confidence: float = Field(ge=0.0, le=1.0)

    parsing_confidence: float = Field(ge=0.0, le=1.0)

    parsing_confidence: float = Field(ge=0.0, le=1.0)
