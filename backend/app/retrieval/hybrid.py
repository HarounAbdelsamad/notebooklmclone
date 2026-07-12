"""Hybrid retrieval: pgvector cosine ANN + Postgres full-text, fused via Reciprocal Rank
Fusion, then reranked with the NVIDIA Nemotron reranker (via OpenRouter)."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Chunk
from app.models.note import Note
from app.services import rerank as rerank_service

logger = logging.getLogger(__name__)

_RRF_K = 60  # standard RRF damping constant


@dataclass
class RetrievedChunk:
    # For note-sourced hits, ``chunk_id`` / ``document_id`` are None and ``note_id`` is set.
    chunk_id: uuid.UUID | None
    document_id: uuid.UUID | None
    content: str
    page_number: int | None
    score: float
    note_id: uuid.UUID | None = None


async def _vector_search(
    db: AsyncSession, notebook_id: uuid.UUID, query_embedding: list[float], limit: int
) -> list[Chunk]:
    result = await db.execute(
        select(Chunk)
        .where(Chunk.notebook_id == notebook_id, Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return list(result.scalars().all())


async def _note_vector_search(
    db: AsyncSession, notebook_id: uuid.UUID, query_embedding: list[float], limit: int
) -> list[Note]:
    result = await db.execute(
        select(Note)
        .where(Note.notebook_id == notebook_id, Note.embedding.isnot(None))
        .order_by(Note.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return list(result.scalars().all())


async def _fts_search(
    db: AsyncSession, notebook_id: uuid.UUID, query_text: str, limit: int
) -> list[Chunk]:
    tsquery = func.plainto_tsquery("english", query_text)
    result = await db.execute(
        select(Chunk)
        .where(Chunk.notebook_id == notebook_id, Chunk.tsv.op("@@")(tsquery))
        .order_by(func.ts_rank_cd(Chunk.tsv, tsquery).desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _rrf_fuse(*ranked_lists: list) -> list:
    """Reciprocal-rank-fuse ranked lists of objects that expose an ``.id`` (Chunk or Note)."""
    scores: dict[uuid.UUID, float] = {}
    objects: dict[uuid.UUID, object] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            scores[item.id] = scores.get(item.id, 0.0) + 1.0 / (_RRF_K + rank + 1)
            objects[item.id] = item
    ordered_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [objects[cid] for cid in ordered_ids]


async def hybrid_retrieve(
    db: AsyncSession,
    notebook_id: uuid.UUID,
    query_text: str,
    query_embedding: list[float],
    top_k: int | None = None,
) -> list:
    """Return fused Chunk/Note candidates. Notes with a populated embedding participate via a
    parallel vector search and are ranked alongside document chunks."""
    top_k = top_k or settings.retrieval_top_k
    vector_hits = await _vector_search(db, notebook_id, query_embedding, top_k)
    fts_hits = await _fts_search(db, notebook_id, query_text, top_k)
    note_hits = await _note_vector_search(db, notebook_id, query_embedding, top_k)
    return _rrf_fuse(vector_hits, fts_hits, note_hits)[:top_k]


async def retrieve_and_rerank(
    db: AsyncSession,
    notebook_id: uuid.UUID,
    query_text: str,
    query_embedding: list[float],
    top_k: int | None = None,
    top_n: int | None = None,
) -> list[RetrievedChunk]:
    """Full retrieval: hybrid candidates -> cross-encoder rerank -> top-N."""
    top_n = top_n or settings.rerank_top_n
    candidates = await hybrid_retrieve(db, notebook_id, query_text, query_embedding, top_k)
    if not candidates:
        return []

    try:
        scores = await rerank_service.rerank(query_text, [c.content for c in candidates])
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda x: x[1], reverse=True)
    except Exception:  # noqa: BLE001 — degrade to RRF ordering if reranker is unavailable
        logger.warning("Reranker unavailable; falling back to RRF ordering", exc_info=True)
        ranked = [(c, 1.0 / (i + 1)) for i, c in enumerate(candidates)]

    return [_to_retrieved(c, float(score)) for c, score in ranked[:top_n]]


def _to_retrieved(candidate, score: float) -> RetrievedChunk:
    if isinstance(candidate, Note):
        return RetrievedChunk(
            chunk_id=None,
            document_id=None,
            content=candidate.content,
            page_number=None,
            score=score,
            note_id=candidate.id,
        )
    return RetrievedChunk(
        chunk_id=candidate.id,
        document_id=candidate.document_id,
        content=candidate.content,
        page_number=candidate.page_number,
        score=score,
    )
