"""Background chat-memory maintenance: roll older turns into a summary and extract facts.

Triggered periodically / after N turns (Phase 4). Keeps the live context window small while
preserving mid-term (summary) and long-term (facts) memory.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import worker_session_scope
from app.models.chat import ChatFact, ChatSummary, Message
from app.prompts.templates import EXTRACT_FACTS_SYSTEM, SUMMARIZE_SYSTEM
from app.services import llm

logger = logging.getLogger(__name__)


def _transcript(messages: list[Message]) -> str:
    return "\n".join(f"{m.role.value}: {m.content}" for m in messages)


async def _load_messages(db: AsyncSession, chat_id: uuid.UUID) -> list[Message]:
    rows = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
    )
    return list(rows.scalars().all())


async def summarize_chat(chat_id: str) -> None:
    async with worker_session_scope() as db:
        messages = await _load_messages(db, uuid.UUID(chat_id))
        if not messages:
            return
        summary = await llm.complete(
            [
                {"role": "system", "content": SUMMARIZE_SYSTEM},
                {"role": "user", "content": _transcript(messages)},
            ],
            max_tokens=512,
        )
        db.add(
            ChatSummary(
                chat_id=uuid.UUID(chat_id),
                summary_text=summary.strip(),
                up_to_message_id=messages[-1].id,
            )
        )
        await db.commit()


async def extract_facts(chat_id: str) -> None:
    async with worker_session_scope() as db:
        messages = await _load_messages(db, uuid.UUID(chat_id))
        if not messages:
            return
        raw = await llm.complete(
            [
                {"role": "system", "content": EXTRACT_FACTS_SYSTEM},
                {"role": "user", "content": _transcript(messages)},
            ],
            max_tokens=256,
        )
        facts = [line.strip("-• ").strip() for line in raw.splitlines() if line.strip()]
        for fact in facts:
            db.add(ChatFact(chat_id=uuid.UUID(chat_id), fact_text=fact))
        await db.commit()
