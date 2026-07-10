"""Upload helpers: bounded reads that reject oversized files with HTTP 413."""

from fastapi import HTTPException, UploadFile, status

_READ_CHUNK = 1024 * 1024  # 1 MiB


async def read_upload_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an ``UploadFile`` into memory, aborting with 413 once ``max_bytes`` is exceeded.

    Reads in bounded chunks so an oversized body is never fully buffered. ``UploadFile.size``
    (when the client provided a Content-Length for the part) is used as a fast pre-check, but the
    streamed byte count is authoritative — the header alone is never trusted.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the maximum upload size of {max_bytes} bytes",
        )

    parts: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds the maximum upload size of {max_bytes} bytes",
            )
        parts.append(chunk)
    return b"".join(parts)
