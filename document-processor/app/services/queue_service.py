from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional

from ..database import DocumentRepository
from ..services.ocr_service import OCRService


@dataclass
class Job:
    document_id: str
    file_type: str
    file_bytes: bytes
    attempts: int = 0


class InMemoryQueueService:
    def __init__(self, *, max_attempts: int = 3) -> None:
        self.queue: "queue.Queue[Optional[Job]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self.max_attempts = max_attempts
        self._stopping = False
        # Services used for processing
        self.repo = DocumentRepository()
        self.ocr = OCRService()

    def _worker(self) -> None:
        while not self._stopping:
            try:
                job = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if job is None:
                self.queue.task_done()
                break
            try:
                self._process(job)
            finally:
                self.queue.task_done()

    def _process(self, job: Job) -> None:
        # retry with exponential backoff
        while job.attempts < self.max_attempts:
            try:
                self.repo.update_status(job.document_id, "processing")
                text, confidence, pages = self.ocr.extract_text(
                    None, job.file_bytes, job.file_type
                )
                self.repo.update_status(job.document_id, "completed", raw_text=text)
                return
            except Exception as e:  # noqa: BLE001
                job.attempts += 1
                if job.attempts >= self.max_attempts:
                    self.repo.update_status(
                        job.document_id, "failed", error_message=str(e)
                    )
                    return
                time.sleep(min(2**job.attempts, 10))

    def enqueue(self, document_id: str, file_type: str, file_bytes: bytes) -> None:
        self.queue.put(Job(document_id, file_type, file_bytes))

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stopping = False
            self._thread = threading.Thread(
                target=self._worker, name="inmem-queue-worker", daemon=True
            )
            self._thread.start()

    async def stop(self) -> None:
        self._stopping = True
        self.queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
