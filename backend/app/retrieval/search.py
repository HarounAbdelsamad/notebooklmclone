"""Unified full-text search across a notebook's documents (chunks), notes, and chat messages."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, Message
from app.models.document import Chunk, Document
from app.models.note import Note
from app.schemas.search import SearchHit, SearchScope

_HEADLINE_OPTS = "StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15"


async def unified_search(
    db: AsyncSession,
    notebook_id: uuid.UUID,
    query: str,
    scopes: list[SearchScope],
    limit: int = 20,
) -> list[SearchHit]:
    tsquery = func.plainto_tsquery("english", query)
    hits: list[SearchHit] = []

    if SearchScope.documents in scopes:
        rank = func.ts_rank_cd(Chunk.tsv, tsquery)
        headline = func.ts_headline("english", Chunk.content, tsquery, _HEADLINE_OPTS)
        rows = await db.execute(
            select(
                Chunk.id,
                Chunk.notebook_id,
                Chunk.document_id,
                Chunk.page_number,
                Document.filename,
                headline,
                rank,
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.notebook_id == notebook_id, Chunk.tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
        )
        for cid, nb_id, doc_id, page, filename, snippet, score in rows:
            hits.append(
                SearchHit(
                    scope=SearchScope.documents,
                    id=cid,
                    title=filename,
                    snippet=snippet,
                    score=float(score),
                    notebook_id=nb_id,
                    document_id=doc_id,
                    page_number=page,
                )
            )

    if SearchScope.notes in scopes:
        rank = func.ts_rank_cd(Note.tsv, tsquery)
        headline = func.ts_headline("english", Note.content, tsquery, _HEADLINE_OPTS)
        rows = await db.execute(
            select(Note.id, Note.notebook_id, Note.title, headline, rank)
            .where(Note.notebook_id == notebook_id, Note.tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
        )
        for nid, nb_id, title, snippet, score in rows:
            hits.append(
                SearchHit(
                    scope=SearchScope.notes,
                    id=nid,
                    title=title,
                    snippet=snippet,
                    score=float(score),
                    notebook_id=nb_id,
                )
            )

    if SearchScope.chats in scopes:
        rank = func.ts_rank_cd(Message.tsv, tsquery)
        headline = func.ts_headline("english", Message.content, tsquery, _HEADLINE_OPTS)
        rows = await db.execute(
            select(Message.id, Chat.notebook_id, Chat.title, headline, rank)
            .join(Chat, Chat.id == Message.chat_id)
            .where(Chat.notebook_id == notebook_id, Message.tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
        )
        for mid, nb_id, title, snippet, score in rows:
            hits.append(
                SearchHit(
                    scope=SearchScope.chats,
                    id=mid,
                    title=title,
                    snippet=snippet,
                    score=float(score),
                    notebook_id=nb_id,
                )
            )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
