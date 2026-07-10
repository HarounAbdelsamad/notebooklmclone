"""Hybrid retrieval: pgvector cosine ANN + Postgres full-text, fused via Reciprocal Rank
Fusion, then reranked with bge-reranker-v2-m3."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Chunk
from app.services import rerank as rerank_service

logger = logging.getLogger(__name__)

_RRF_K = 60  # standard RRF damping constant


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    page_number: int | None
    score: float


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


def _rrf_fuse(*ranked_lists: list[Chunk]) -> list[Chunk]:
    scores: dict[uuid.UUID, float] = {}
    objects: dict[uuid.UUID, Chunk] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (_RRF_K + rank + 1)
            objects[chunk.id] = chunk
    ordered_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [objects[cid] for cid in ordered_ids]


async def hybrid_retrieve(
    db: AsyncSession,
    notebook_id: uuid.UUID,
    query_text: str,
    query_embedding: list[float],
    top_k: int | None = None,
) -> list[Chunk]:
    top_k = top_k or settings.retrieval_top_k
    vector_hits = await _vector_search(db, notebook_id, query_embedding, top_k)
    fts_hits = await _fts_search(db, notebook_id, query_text, top_k)
    return _rrf_fuse(vector_hits, fts_hits)[:top_k]


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

    return [
        RetrievedChunk(
            chunk_id=c.id,
            document_id=c.document_id,
            content=c.content,
            page_number=c.page_number,
            score=float(score),
        )
        for c, score in ranked[:top_n]
    ]
