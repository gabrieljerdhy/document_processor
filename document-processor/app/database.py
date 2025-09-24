import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

DB_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "app.db"))


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL,
                raw_text TEXT,
                parsed_data TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_logs (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


@contextmanager
def get_conn(dict_mode: bool = False):
    conn = sqlite3.connect(DB_PATH)
    if dict_mode:
        conn.row_factory = _dict_factory
    try:
        yield conn
    finally:
        conn.close()


class DocumentRepository:
    def create_document(self, file_name: str, file_type: str, file_size: int, uploaded_by: str = "system") -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        doc_id = str(uuid.uuid4())
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, file_name, file_type, file_size, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (doc_id, file_name, file_type, file_size, now, now),
            )
            conn.commit()
        self.log_action(doc_id, "create_document", "pending", {"uploaded_by": uploaded_by})
        return {"id": doc_id, "status": "pending", "created_at": now, "updated_at": now}

    def update_status(
        self,
        document_id: str,
        status: str,
        *,
        error_message: Optional[str] = None,
        raw_text: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = ?, error_message = ?, raw_text = COALESCE(?, raw_text), parsed_data = COALESCE(?, parsed_data), updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    error_message,
                    raw_text,
                    json.dumps(parsed_data) if parsed_data is not None else None,
                    now,
                    document_id,
                ),
            )
            conn.commit()
        self.log_action(document_id, "update_status", status, {"error": error_message})

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with get_conn(dict_mode=True) as conn:
            cur = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = cur.fetchone()
            if row and row.get("parsed_data"):
                try:
                    row["parsed_data"] = json.loads(row["parsed_data"]) if row["parsed_data"] else None
                except Exception:
                    row["parsed_data"] = None
            return row

    def log_action(self, document_id: str, action: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO processing_logs (id, document_id, action, status, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    document_id,
                    action,
                    status,
                    json.dumps(details or {}),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()


repo = DocumentRepository()
init_db()

