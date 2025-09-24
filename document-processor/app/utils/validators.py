from typing import Tuple
from fastapi import UploadFile

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file(file: UploadFile) -> Tuple[str, int]:
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Allowed: pdf, png, jpg, docx")

    # Peek size by reading into memory (acceptable for 10MB max)
    content = file.file.read()
    size = len(content)
    if size > MAX_FILE_SIZE:
        raise ValueError("File too large. Max 10MB")

    # reset cursor for further processing
    file.file.seek(0)
    return ext, size

