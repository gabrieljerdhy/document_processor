# Document Processing System - Test Project Specification

## Project Overview
Build a production-ready FastAPI service for document processing that demonstrates enterprise patterns, error handling, and data pipeline capabilities.

## Core Requirements

### 1. API Endpoints

```python
POST /documents/upload
- Accept PDF, PNG, JPG, DOCX files (max 10MB)
- Return document_id and processing status
- Validate file types and size

GET /documents/{document_id}
- Return document metadata and extracted content
- Include processing status and timestamps

GET /documents/{document_id}/text
- Return only extracted text content
- Support format parameter (plain, json, markdown)

POST /documents/{document_id}/parse
- Parse extracted text into structured data
- Support different parser types (invoice, receipt, contract)

GET /health
- Return service health and dependencies status
```

### 2. Pydantic Models

```python
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
    confidence_score: float
    metadata: Dict[str, Any]
    pages: Optional[int] = None
    language: Optional[str] = "en"

class ParsedData(BaseModel):
    document_type: str
    fields: Dict[str, Any]
    validation_errors: List[str] = []
    parsing_confidence: float
```

### 3. Technical Implementation

**OCR Processing:**
- Use pytesseract for image OCR
- Use PyPDF2 or pdfplumber for PDF text extraction
- Implement fallback to OCR if PDF text extraction fails
- Track confidence scores

**Queue System:**
- Implement async processing with background tasks
- Use Redis or in-memory queue for job management
- Include retry logic (max 3 attempts)
- Exponential backoff for retries

**Error Handling:**
- Custom exception classes for different error types
- Proper HTTP status codes
- Detailed error messages in development, sanitized in production
- Circuit breaker pattern for OCR service

### 4. Data Storage

```python
# Use SQLite for simplicity, structure for easy migration to PostgreSQL
documents_table:
  - id: UUID
  - file_name: str
  - file_type: str
  - file_size: int
  - status: str
  - raw_text: text
  - parsed_data: json
  - error_message: text
  - created_at: timestamp
  - updated_at: timestamp

processing_logs_table:
  - id: UUID
  - document_id: UUID
  - action: str
  - status: str
  - details: json
  - created_at: timestamp
```

### 5. Performance Requirements

- Process 1-page PDF in < 5 seconds
- Handle concurrent uploads (test with 10 simultaneous)
- Implement request rate limiting (10 requests/minute)
- Cache extracted text for 1 hour

## Deliverables

### 1. Code Structure
```
document-processor/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── services/
│   │   ├── ocr_service.py
│   │   ├── parser_service.py
│   │   └── storage_service.py
│   ├── api/
│   │   ├── routes.py
│   │   └── dependencies.py
│   └── utils/
│       ├── validators.py
│       └── exceptions.py
├── tests/
│   ├── test_api.py
│   ├── test_services.py
│   └── sample_files/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### 2. Testing Requirements
- Unit tests for all services
- Integration tests for API endpoints
- Include sample test files (PDF, image)
- Test error conditions (corrupted files, timeout)
- Achieve 70% code coverage

### 3. Documentation

**README must include:**
- Architecture overview
- Setup instructions (local and Docker)
- API documentation with curl examples
- Configuration options
- Performance considerations
- Known limitations

**Example API calls:**
```bash
# Upload document
curl -X POST "http://localhost:8000/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice.pdf"

# Get extracted text
curl "http://localhost:8000/documents/{id}/text?format=json"
```

### 4. Docker Setup
- Multi-stage Dockerfile for small image size
- docker-compose.yml with Redis and app services
- Environment variable configuration
- Health checks included

## Evaluation Criteria

### Must Have (Pass/Fail)
- [ ] All endpoints working with correct status codes
- [ ] File upload and OCR extraction functional
- [ ] Proper error handling (no crashes on bad input)
- [ ] Docker setup works with single command
- [ ] Basic tests passing

### Quality Indicators
- [ ] Clean code structure and organization
- [ ] Comprehensive error messages
- [ ] Performance optimizations implemented
- [ ] Extensive test coverage
- [ ] Clear documentation

### Bonus Points
- [ ] Implement WebSocket for real-time processing status
- [ ] Add Prometheus metrics endpoint
- [ ] Include pre-commit hooks for code quality
- [ ] Implement content-based file type detection
- [ ] Add virus scanning simulation

## Submission

1. GitHub repository (public or provide access)
2. Deployed demo (optional - Render, Railway, etc.)
3. Brief write-up on:
   - AI tools used and how
   - Challenges faced and solutions
   - Performance optimization decisions
   - What you'd improve with more time

## Timeline
- 48 hours from start confirmation
- Partial credit for functional but incomplete solutions
- Communication appreciated if blockers encountered