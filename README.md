# Document Processing Service (FastAPI)

FastAPI-based document processing service that accepts PDF/PNG/JPG/DOCX uploads, extracts text (PDF text + OCR fallback for PDFs and images), and parses into structured data (invoice/receipt/contract). Includes health checks, in-memory queue with retry/backoff, SQLite storage, rate limiting, and Docker support.

For full, service-level documentation, see document-processor/README.md.

## Repository layout

- document-processor/
  - app/ … FastAPI application code (APIs, services, database, utils)
  - tests/ … unit/integration tests and sample assets
  - Dockerfile, docker-compose.yml
  - README.md (detailed service documentation)
- gabriel-document-processing-test.md … original specification (if present)

## Quick Start (local)

1. Prerequisites

   - Python 3.11+
   - Optional: Tesseract OCR for local OCR. If not installed locally, prefer Docker which bundles it.

2. Create a virtual environment and install dependencies

   - Using uv (recommended)
     ```bash
     uv venv .venv
     # Git Bash:
     source .venv/Scripts/activate
     # cmd/PowerShell:
     # .venv\Scripts\activate
     uv pip install -r requirements.txt
     ```
   - Or with built-in venv + pip
     ```bash
     python -m venv .venv
     # Git Bash:
     source .venv/Scripts/activate
     # cmd/PowerShell:
     # .venv\Scripts\activate
     pip install -r requirements.txt
     ```

3. Run tests

   ```bash
   cd document-processor
   PYTHONPATH=. pytest -q
   ```

4. Start the API

   ```bash
   cd document-processor
   uvicorn app.main:app --reload
   ```

5. Open the docs
   - http://localhost:8000/docs

## Quick Start (Docker)

From the document-processor directory:

```bash
cd document-processor
# Build and run
docker compose up --build -d

# Check health
curl http://localhost:8000/health
# Expect: {"status":"ok", ...}

# View logs (follow)
docker compose logs -f app

# Stop and clean up
docker compose down
# or to remove volumes as well
# docker compose down -v
```

## Supported file types and limits

- Types: PDF, PNG, JPG, DOCX
- Max file size: 10 MB (oversized uploads return HTTP 400)

## Core endpoints

- POST /documents/upload
- GET /documents/{document_id}
- GET /documents/{document_id}/text?format=plain|json|markdown
- POST /documents/{document_id}/parse?parser_type=invoice|receipt|contract
- GET /health

## Typical workflow (curl)

```bash
# 1) Upload a document
curl -s -X POST "http://localhost:8000/documents/upload" \
 -H "Content-Type: multipart/form-data" \
 -F "file=@/path/to/file.pdf" | tee upload.json

# 2) Poll status until completed/failed
DOC_ID=$(python - <<'PY'
import sys, json
print(json.load(open('upload.json'))['document_id'])
PY
)
while true; do
  BODY=$(curl -s "http://localhost:8000/documents/$DOC_ID")
  echo "$BODY" | grep -q '"status":"completed"' && break
  echo "$BODY" | grep -q '"status":"failed"' && break
  sleep 0.5
done

# 3) Get extracted text (as JSON)
curl -s "http://localhost:8000/documents/$DOC_ID/text?format=json"

# 4) Parse into structured fields (example: invoice)
curl -s -X POST "http://localhost:8000/documents/$DOC_ID/parse?parser_type=invoice"
```

## Sample OCR demo (bundled test image)

From document-processor, use the included sample PNG to see OCR end-to-end:

```bash
cd document-processor
# 1) Upload the sample image
curl -s -S -o upload_hello.json -w 'HTTP:%{http_code}\n' \
  -F 'file=@tests/sample_files/hello.png;type=image/png' \
  http://localhost:8000/documents/upload

# 2) Extract document_id
DOC_ID=$(python - <<'PY'
import json; print(json.load(open('upload_hello.json'))['document_id'])
PY
)

# 3) Poll until done
for i in 1 2 3 4 5 6 7 8 9 10; do
  BODY=$(curl -s "http://localhost:8000/documents/$DOC_ID")
  echo poll:$i $BODY
  echo "$BODY" | grep -q '"status":"completed"' && break
  echo "$BODY" | grep -q '"status":"failed"' && break
  sleep 0.7
done

# 4) Fetch text (should contain HELLO)
curl -s "http://localhost:8000/documents/$DOC_ID/text?format=plain" | head -c 200; echo
```

## Configuration (env vars)

- DATABASE_PATH: SQLite DB path (default: app/app.db inside container; ./app.db locally)
- APP_ENV: dev | prod (controls error detail level)
- Rate limit: 10 requests/min per client (defined in app/main.py)
- Text cache TTL: 3600 seconds (see app/api/routes.py)

## Architecture overview

- FastAPI app with routers (app/api)
- OCR service with circuit breaker (app/services/ocr_service.py)
- Rule-based parser (invoice/receipt/contract) (app/services/parser_service.py)
- In-memory queue with background worker + retries + exponential backoff (app/services/queue_service.py)
- SQLite repository + processing logs (app/database.py)
- Health checks with deep dependency probes

## Testing & coverage

From document-processor (coverage enforced at e=70% via pytest.ini):

```bash
PYTHONPATH=. pytest -q
# Optional explicit report:
PYTHONPATH=. pytest --cov=app --cov-report=term-missing
```

## Troubleshooting

- 429 Too Many Requests
  - You hit the per-client rate limit (10/min). Wait ~60s and retry.
- 409 Conflict on parse
  - Parsing requires the document to be processed. Poll GET /documents/{id} until status is "completed".
- OCR errors locally
  - If Tesseract is not installed locally, use Docker (it includes tesseract-ocr) or install it on your system.
- Docker health
  - docker compose ps
  - docker compose logs -f app

## Where to go next

- See document-processor/README.md for deeper details, more examples, and maintenance notes.
- Refer to gabriel-document-processing-test.md for the full original specification and acceptance criteria (if present in this repo).
