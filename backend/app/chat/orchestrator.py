"""RAG chat orchestration: rewrite -> embed -> hybrid retrieve -> rerank -> stream answer.

Yields Server-Sent Events (sse-starlette dict form). The assistant message and its citations
are persisted once the stream completes.
"""

import json
import logging
import re
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.memory import RECENT_MESSAGE_LIMIT, build_memory
from app.embedding.client import embed_query
from app.models.chat import Chat, Message, MessageCitation
from app.models.enums import MessageRole
from app.models.workspace import Notebook
from app.prompts.templates import build_answer_messages, build_rewrite_messages
from app.retrieval.hybrid import RetrievedChunk, retrieve_and_rerank
from app.services import llm
from app.utils.tokenizer import count_tokens

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(r"\[(\d+)\]")

# Once a chat grows past the live recent window, roll older turns into a summary + facts. Fire
# only on interval boundaries (each turn adds 2 messages) so we don't re-summarize every message
# or schedule duplicate jobs.
MAINTENANCE_INTERVAL_MESSAGES = 8


def _maintenance_due(message_count: int) -> bool:
    return (
        message_count > RECENT_MESSAGE_LIMIT and message_count % MAINTENANCE_INTERVAL_MESSAGES == 0
    )


async def _schedule_memory_maintenance(db: AsyncSession, chat_id: uuid.UUID) -> None:
    """Enqueue rolling-summary + fact-extraction jobs when the chat crosses an interval
    boundary. Enqueue failures are logged and swallowed so they never break the chat response."""
    try:
        count = await db.scalar(
            select(func.count()).select_from(Message).where(Message.chat_id == chat_id)
        )
        if count is None or not _maintenance_due(count):
            return
        # Lazy import keeps the Celery app out of the request-path import graph.
        from app.workers.tasks import extract_chat_facts, summarize_chat

        summarize_chat.delay(str(chat_id))
        extract_chat_facts.delay(str(chat_id))
    except Exception:  # noqa: BLE001 — scheduling is best-effort; never fail the response
        logger.warning("Failed to schedule chat memory maintenance", exc_info=True)


def _sse(event: str, data) -> dict:
    return {"event": event, "data": data if isinstance(data, str) else json.dumps(data)}


async def _resolve_chat(
    db: AsyncSession, notebook: Notebook, chat_id: uuid.UUID | None, question: str
) -> Chat:
    if chat_id is not None:
        row = await db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.notebook_id == notebook.id)
        )
        chat = row.scalar_one_or_none()
        if chat is None:
            raise ValueError("Chat not found")
        return chat
    title = (question[:60] + "…") if len(question) > 60 else question
    chat = Chat(notebook_id=notebook.id, title=title or "New chat")
    db.add(chat)
    await db.flush()
    return chat


async def _rewrite_query(recent_turns: str, question: str) -> str:
    if not recent_turns.strip():
        return question
    try:
        rewritten = await llm.complete(
            build_rewrite_messages(recent_turns, question), max_tokens=128
        )
        return rewritten.strip() or question
    except Exception:  # noqa: BLE001
        logger.warning("Query rewrite failed; using raw question", exc_info=True)
        return question


def _select_citations(answer: str, sources: list[RetrievedChunk]) -> list[RetrievedChunk]:
    referenced = {int(m) for m in _CITATION_RE.findall(answer)}
    picked = [sources[n - 1] for n in sorted(referenced) if 1 <= n <= len(sources)]
    return picked or sources


async def stream_answer(
    db: AsyncSession,
    notebook: Notebook,
    chat_id: uuid.UUID | None,
    question: str,
) -> AsyncIterator[dict]:
    try:
        chat = await _resolve_chat(db, notebook, chat_id, question)
        memory = await build_memory(db, chat.id)

        db.add(
            Message(
                chat_id=chat.id,
                role=MessageRole.user,
                content=question,
                token_count=count_tokens(question),
            )
        )
        await db.flush()

        recent_turns = "\n".join(f"{m.role.value}: {m.content}" for m in memory.recent)
        search_query = await _rewrite_query(recent_turns, question)

        sources: list[RetrievedChunk] = []
        try:
            query_embedding = await embed_query(search_query)
            sources = await retrieve_and_rerank(db, notebook.id, search_query, query_embedding)
        except Exception:  # noqa: BLE001 — retrieval failure degrades to an ungrounded answer
            logger.warning("Retrieval failed; answering without sources", exc_info=True)

        numbered = [(i + 1, s.content) for i, s in enumerate(sources)]
        messages = build_answer_messages(question, numbered, memory.as_block())

        yield _sse("start", {"chat_id": str(chat.id)})

        answer_parts: list[str] = []
        async for token in llm.stream_chat(messages):
            answer_parts.append(token)
            yield _sse("token", token)
        answer = "".join(answer_parts)

        assistant = Message(
            chat_id=chat.id,
            role=MessageRole.assistant,
            content=answer,
            token_count=count_tokens(answer),
        )
        db.add(assistant)
        await db.flush()

        cited = _select_citations(answer, sources)
        citations_payload = []
        for rank, src in enumerate(cited):
            db.add(
                MessageCitation(
                    message_id=assistant.id,
                    chunk_id=src.chunk_id,
                    document_id=src.document_id,
                    snippet=src.content[:500],
                    page_number=src.page_number,
                    score=src.score,
                    rank=rank,
                )
            )
            citations_payload.append(
                {
                    "chunk_id": str(src.chunk_id) if src.chunk_id else None,
                    "document_id": str(src.document_id) if src.document_id else None,
                    "snippet": src.content[:500],
                    "page_number": src.page_number,
                    "score": src.score,
                    "rank": rank,
                }
            )
        await db.commit()

        # Turn is persisted; roll memory forward if the chat has outgrown the recent window.
        await _schedule_memory_maintenance(db, chat.id)

        yield _sse("citations", citations_payload)
        yield _sse("done", {"chat_id": str(chat.id), "message_id": str(assistant.id)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("stream_answer failed")
        await db.rollback()
        yield _sse("error", {"message": str(exc)})
