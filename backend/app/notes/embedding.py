"""Embed a note's content so it participates in hybrid retrieval.

Runs inside the Celery worker (via ``asyncio.run``) like the ingestion pipeline, using a per-task
NullPool session. An embedding failure is logged and swallowed — it must never break note
create/update, which already committed before this job was enqueued.
"""

import logging
import uuid

from app.db.session import worker_session_scope
from app.embedding.client import embed_texts
from app.models.note import Note

logger = logging.getLogger(__name__)


def note_embedding_text(title: str, content: str) -> str:
    """The text embedded for a note — title + body, mirroring the FTS ``tsv`` composition."""
    return f"{title}\n\n{content}".strip()


async def embed_note(note_id: str) -> None:
    async with worker_session_scope() as db:
        note = await db.get(Note, uuid.UUID(note_id))
        if note is None:
            logger.warning("Note embedding skipped: note %s not found", note_id)
            return

        text = note_embedding_text(note.title, note.content)
        if not text:
            note.embedding = None
            await db.commit()
            return

        try:
            vectors = await embed_texts([text])
        except Exception:  # noqa: BLE001 — external embed call must not crash the worker
            logger.warning("Note embedding failed for %s", note_id, exc_info=True)
            return

        note.embedding = vectors[0]
        await db.commit()
        logger.info("Embedded note %s", note_id)
