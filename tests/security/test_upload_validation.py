from __future__ import annotations

import asyncio

import pytest
from app.services.resume_parser import parse_upload
from fastapi import HTTPException, UploadFile


def test_rejects_unsupported_upload_extension() -> None:
    upload = UploadFile(filename="resume.exe", file=binary_file(b"not allowed"))
    upload.headers = {"content-type": "application/octet-stream"}

    with pytest.raises(HTTPException) as exc:
        asyncio.run(parse_upload(upload))

    assert exc.value.status_code == 400


def binary_file(content: bytes):
    import io

    return io.BytesIO(content)
