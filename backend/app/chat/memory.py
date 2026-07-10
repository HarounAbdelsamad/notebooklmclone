"""Chat memory assembly: summaries (mid-term) + facts (long-term) + recent messages."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatFact, ChatSummary, Message

RECENT_MESSAGE_LIMIT = 8


@dataclass
class MemoryContext:
    summary: str | None = None
    facts: list[str] = field(default_factory=list)
    recent: list[Message] = field(default_factory=list)

    def as_block(self) -> str:
        parts: list[str] = []
        if self.summary:
            parts.append(f"Summary of earlier conversation:\n{self.summary}")
        if self.facts:
            parts.append("Known facts:\n" + "\n".join(f"- {f}" for f in self.facts))
        if self.recent:
            turns = "\n".join(f"{m.role.value}: {m.content}" for m in self.recent)
            parts.append(f"Recent turns:\n{turns}")
        return "\n\n".join(parts)


async def build_memory(db: AsyncSession, chat_id: uuid.UUID) -> MemoryContext:
    summary_row = await db.execute(
        select(ChatSummary)
        .where(ChatSummary.chat_id == chat_id)
        .order_by(ChatSummary.created_at.desc())
        .limit(1)
    )
    summary = summary_row.scalar_one_or_none()

    facts_rows = await db.execute(
        select(ChatFact.fact_text)
        .where(ChatFact.chat_id == chat_id)
        .order_by(ChatFact.created_at.desc())
        .limit(20)
    )
    facts = [row[0] for row in facts_rows]

    recent_rows = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(RECENT_MESSAGE_LIMIT)
    )
    recent = list(reversed(recent_rows.scalars().all()))

    return MemoryContext(
        summary=summary.summary_text if summary else None,
        facts=facts,
        recent=recent,
    )
