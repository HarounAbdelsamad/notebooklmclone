import io

import pytest
from fastapi import HTTPException, UploadFile

from app.utils.uploads import read_upload_capped


def _upload(data: bytes, size: int | None = None) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), size=size, filename="f.bin")


async def test_read_upload_capped_returns_bytes_within_limit():
    data = b"hello world"
    result = await read_upload_capped(_upload(data), max_bytes=1024)
    assert result == data


async def test_read_upload_capped_rejects_oversized_stream():
    data = b"x" * 200
    with pytest.raises(HTTPException) as exc:
        await read_upload_capped(_upload(data), max_bytes=100)
    assert exc.value.status_code == 413


async def test_read_upload_capped_fast_rejects_via_size_header():
    # Content-Length pre-check: reject before reading the body.
    with pytest.raises(HTTPException) as exc:
        await read_upload_capped(_upload(b"", size=10_000), max_bytes=100)
    assert exc.value.status_code == 413


async def test_read_upload_capped_at_exact_limit_is_allowed():
    data = b"x" * 100
    result = await read_upload_capped(_upload(data), max_bytes=100)
    assert result == data
