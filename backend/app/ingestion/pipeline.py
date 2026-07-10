"""Document ingestion pipeline: extract -> clean -> chunk -> embed -> store.

Runs inside the Celery worker (via ``asyncio.run``). Each stage updates the document's
status so the frontend can show progress, and any failure marks the document ``failed``.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import worker_session_scope
from app.embedding.client import embed_texts, embed_texts_sync
from app.models.document import Chunk, Document
from app.models.enums import DocumentStatus
from app.parsing import get_parser
from app.parsing.base import TextBlock
from app.utils.chunking import semantic_chunks
from app.utils.text import clean_text

logger = logging.getLogger(__name__)


async def _set_status(
    db: AsyncSession, document: Document, status: DocumentStatus, error: str | None = None
) -> None:
    document.status = status
    if error is not None:
        document.error = error
    await db.commit()


async def run_ingestion(document_id: str) -> None:
    async with worker_session_scope() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        if document is None:
            logger.warning("Ingestion skipped: document %s not found", document_id)
            return
        try:
            await _run(db, document)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestion failed for %s", document_id)
            await _set_status(db, document, DocumentStatus.failed, error=str(exc)[:2000])


async def _run(db: AsyncSession, document: Document) -> None:
    # ---- extract ----
    await _set_status(db, document, DocumentStatus.extracting)
    data: bytes | None = None
    if document.storage_path:
        from app.services.storage import download_bytes

        data = await download_bytes(document.storage_path)
    parser = get_parser(document.source_type)
    parsed = await asyncio.to_thread(
        parser.parse, data=data, url=document.source_url, filename=document.filename
    )

    # ---- clean ----
    await _set_status(db, document, DocumentStatus.cleaning)
    blocks = [
        TextBlock(text=clean_text(b.text), page_number=b.page_number)
        for b in parsed.blocks
        if b.text and b.text.strip()
    ]
    document.char_count = sum(len(b.text) for b in blocks)
    document.page_count = parsed.page_count

    # ---- chunk (semantic, with recursive fallback inside) ----
    await _set_status(db, document, DocumentStatus.chunking)
    chunks = await asyncio.to_thread(semantic_chunks, blocks, embed_texts_sync)
    if not chunks:
        raise ValueError("No text could be extracted from the document")

    # ---- embed ----
    await _set_status(db, document, DocumentStatus.embedding)
    embeddings = await embed_texts([c.content for c in chunks])

    # ---- store ----
    await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        db.add(
            Chunk(
                document_id=document.id,
                notebook_id=document.notebook_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                embedding=embedding,
            )
        )
    document.status = DocumentStatus.ready
    document.processed_at = datetime.now(UTC)
    await db.commit()
    logger.info("Ingested document %s (%d chunks)", document.id, len(chunks))
