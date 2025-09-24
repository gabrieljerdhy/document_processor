from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Optional, Tuple

from ..utils.exceptions import CircuitBreakerOpenError, OCRServiceError

try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - optional dep
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

try:
    import pypdfium2 as pdfium  # type: ignore
except Exception:  # pragma: no cover
    pdfium = None  # type: ignore


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_timeout_sec: int = 60
    failures: int = 0
    opened_at: Optional[float] = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time() - self.opened_at >= self.reset_timeout_sec:
            # half-open
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time()


class OCRService:
    def __init__(self) -> None:
        self.cb = CircuitBreaker()

    def extract_text(
        self, file_path: Optional[str], file_bytes: bytes, file_type: str
    ) -> Tuple[str, float, Optional[int]]:
        if not self.cb.allow():
            raise CircuitBreakerOpenError("OCR circuit breaker is open")
        try:
            if file_type == "pdf":
                text, pages = self._extract_pdf(file_path, file_bytes)
                if text.strip():
                    self.cb.record_success()
                    return text, 0.85, pages
                # Attempt OCR fallback by rasterizing pages if available
                ocr_text = self._ocr_pdf_pages(file_bytes)
                self.cb.record_success()
                if ocr_text.strip():
                    return ocr_text, 0.6, pages
                return "", 0.2, pages
            elif file_type in {"png", "jpg", "jpeg"}:
                text = self._extract_image(file_bytes)
                self.cb.record_success()
                return text, (0.8 if text.strip() else 0.2), None
            elif file_type == "docx":
                # Minimal placeholder: not implementing full docx parsing here
                self.cb.record_success()
                return "", 0.1, None
            else:
                raise OCRServiceError("Unsupported file type for OCR")
        except CircuitBreakerOpenError:
            raise
        except Exception as e:
            self.cb.record_failure()
            raise OCRServiceError(str(e)) from e

    def _extract_pdf(
        self, file_path: Optional[str], file_bytes: bytes
    ) -> Tuple[str, Optional[int]]:
        # Prefer pdfplumber if available (better text extraction)
        if pdfplumber is not None:
            import io

            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
                return "\n".join(pages_text), len(pdf.pages)
        # Fallback to pypdf
        if PdfReader is not None:
            import io

            reader = PdfReader(io.BytesIO(file_bytes))
            texts = []
            for page in reader.pages:
                try:
                    texts.append(page.extract_text() or "")
                except Exception:
                    texts.append("")
            return "\n".join(texts), len(reader.pages)
        return "", None

    def _ocr_pdf_pages(self, file_bytes: bytes) -> str:
        if pdfium is None or pytesseract is None or Image is None:
            return ""
        try:
            import io

            pdf = pdfium.PdfDocument(io.BytesIO(file_bytes))
            texts = []
            for i in range(len(pdf)):
                page = pdf[i]
                # Render at ~150 DPI (scale = dpi / 72)
                pil_image = page.render(scale=150 / 72).to_pil()
                texts.append(pytesseract.image_to_string(pil_image))
            return "\n".join(texts)
        except Exception:
            return ""

    def _extract_image(self, file_bytes: bytes) -> str:
        if pytesseract is None or Image is None:
            return ""
        import io

        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
