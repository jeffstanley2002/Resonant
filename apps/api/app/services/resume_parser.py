from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status

from app.core.cache import TTLCache
from app.core.config import settings
from app.services.sanitization import sanitize_untrusted_text

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


@dataclass(frozen=True)
class ParsedResume:
    text: str
    warnings: list[str]


_PARSED_RESUME_CACHE: TTLCache[ParsedResume] = TTLCache(max_size=64, ttl_seconds=30 * 60)


async def parse_upload(file: UploadFile) -> ParsedResume:
    filename = file.filename or ""
    extension = _extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported resume type. Upload PDF, DOCX, or TXT.",
        )
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type")

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    cache_key = hashlib.sha256(extension.encode("utf-8") + b":" + content).hexdigest()
    cached = _PARSED_RESUME_CACHE.get(cache_key)
    if cached is not None:
        return cached

    text = _extract_text(content, extension)
    text = normalize_text(text)
    text, sanitize_warnings = sanitize_untrusted_text(text)
    if len(text) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume did not contain enough readable text",
        )

    warnings: list[str] = [*sanitize_warnings]
    if len(text) < 500:
        warnings.append("Resume text is short; recommendations may be less precise.")

    parsed = ParsedResume(text=text, warnings=warnings)
    _PARSED_RESUME_CACHE.set(cache_key, parsed)
    return parsed


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extension(filename: str) -> str:
    safe = filename.lower().split("/")[-1].split("\\")[-1]
    if "." not in safe:
        return ""
    return "." + safe.rsplit(".", 1)[1]


def _extract_text(content: bytes, extension: str) -> str:
    if extension == ".txt":
        return content.decode("utf-8", errors="replace")
    if extension == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # pragma: no cover - depends on optional parser internals
            raise HTTPException(status_code=400, detail="Could not parse PDF") from exc
    if extension == ".docx":
        try:
            from docx import Document

            doc = Document(io.BytesIO(content))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as exc:  # pragma: no cover - depends on optional parser internals
            raise HTTPException(status_code=400, detail="Could not parse DOCX") from exc
    return ""
