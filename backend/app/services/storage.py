"""Object storage on Supabase Storage, with a local-filesystem fallback for dev.

When Supabase is unconfigured (no URL/key), files are written under ``./uploads`` so the
whole pipeline can be exercised locally without cloud credentials.
"""

import asyncio
import re
import uuid
from functools import lru_cache
from pathlib import Path

from app.config import settings

_LOCAL_ROOT = Path("uploads")
_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _use_supabase() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_key)


@lru_cache
def _supabase_client():
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_key)


def build_storage_path(notebook_id: uuid.UUID, filename: str) -> str:
    safe = _SAFE_RE.sub("_", filename).strip("_") or "file"
    return f"{notebook_id}/{uuid.uuid4().hex}_{safe}"


async def upload_bytes(path: str, data: bytes, content_type: str | None = None) -> str:
    if _use_supabase():

        def _do() -> None:
            client = _supabase_client()
            client.storage.from_(settings.supabase_storage_bucket).upload(
                path,
                data,
                {"content-type": content_type or "application/octet-stream", "upsert": "true"},
            )

        await asyncio.to_thread(_do)
        return path

    def _write() -> None:
        full = _LOCAL_ROOT / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    await asyncio.to_thread(_write)
    return path


async def download_bytes(path: str) -> bytes:
    if _use_supabase():

        def _do() -> bytes:
            client = _supabase_client()
            return client.storage.from_(settings.supabase_storage_bucket).download(path)

        return await asyncio.to_thread(_do)

    def _read() -> bytes:
        return (_LOCAL_ROOT / path).read_bytes()

    return await asyncio.to_thread(_read)


async def create_signed_upload_url(path: str) -> str:
    """Production direct-to-storage upload URL (bypasses the API server for large files)."""
    if not _use_supabase():
        raise RuntimeError("Signed upload URLs require Supabase Storage to be configured")

    def _do() -> str:
        client = _supabase_client()
        res = client.storage.from_(settings.supabase_storage_bucket).create_signed_upload_url(path)
        return res["signed_url"] if isinstance(res, dict) else res

    return await asyncio.to_thread(_do)
