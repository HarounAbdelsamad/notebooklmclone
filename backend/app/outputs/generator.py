"""Generate notebook-level outputs (summary, FAQ, study guide, briefing, timeline)."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import worker_session_scope
from app.models.document import Chunk
from app.models.output import GeneratedOutput
from app.prompts.templates import build_output_messages
from app.services import llm

logger = logging.getLogger(__name__)

# Bound the amount of source text fed to the LLM for a single generation.
_MAX_SOURCE_CHUNKS = 60


async def _collect_sources(db: AsyncSession, notebook_id: uuid.UUID) -> str:
    rows = await db.execute(
        select(Chunk.content)
        .where(Chunk.notebook_id == notebook_id)
        .order_by(Chunk.document_id, Chunk.chunk_index)
        .limit(_MAX_SOURCE_CHUNKS)
    )
    return "\n\n".join(row[0] for row in rows)


async def run_generate_output(output_id: str) -> None:
    async with worker_session_scope() as db:
        output = await db.get(GeneratedOutput, uuid.UUID(output_id))
        if output is None:
            logger.warning("generate_output skipped: %s not found", output_id)
            return
        try:
            sources = await _collect_sources(db, output.notebook_id)
            if not sources.strip():
                output.content = "_No source content available yet. Upload documents first._"
            else:
                messages = build_output_messages(output.type.value, sources)
                output.content = await llm.complete(messages, max_tokens=2048)
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Output generation failed for %s", output_id)
            output.content = f"_Generation failed: {exc}_"
            await db.commit()
