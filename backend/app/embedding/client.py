"""NVIDIA Llama-Nemotron embeddings via OpenRouter's OpenAI-compatible ``/embeddings`` endpoint.

``nvidia/llama-nemotron-embed-vl-1b-v2:free`` is multilingual and outputs 2048-dim vectors, but is
Matryoshka-trained: the leading dimensions form a valid lower-dimensional embedding. We slice every
vector to ``settings.embedding_dim`` (1024, to match the pinned pgvector column / HNSW index) and
re-L2-normalize it. Queries and passages use the same model. Sync + async variants are provided
because the Celery ingestion pipeline needs a sync embedder for semantic chunking.
"""

import math

import httpx

from app.config import settings

_BATCH = 64


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.effective_embeddings_api_key}"}


def _payload(texts: list[str]) -> dict:
    return {"model": settings.embedding_model, "input": texts}


def _to_pinned_dim(vec: list[float]) -> list[float]:
    """Matryoshka-truncate to ``settings.embedding_dim`` and L2-normalize."""
    dim = settings.embedding_dim
    if len(vec) < dim:
        raise ValueError(
            f"Embedding has {len(vec)} dims; need at least {dim} to truncate to the pinned dim"
        )
    sliced = vec[:dim]
    norm = math.sqrt(sum(x * x for x in sliced))
    if norm == 0.0:
        return sliced
    return [x / norm for x in sliced]


def _parse(data: dict) -> list[list[float]]:
    # OpenAI-compatible response: {"data": [{"embedding": [...], "index": i}, ...]}
    items = sorted(data["data"], key=lambda d: d.get("index", 0))
    return [_to_pinned_dim(item["embedding"]) for item in items]


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    out: list[list[float]] = []
    with httpx.Client(base_url=settings.embeddings_base_url, timeout=60.0) as client:
        for i in range(0, len(texts), _BATCH):
            batch = texts[i : i + _BATCH]
            resp = client.post("/embeddings", json=_payload(batch), headers=_headers())
            resp.raise_for_status()
            out.extend(_parse(resp.json()))
    return out


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    out: list[list[float]] = []
    async with httpx.AsyncClient(base_url=settings.embeddings_base_url, timeout=60.0) as client:
        for i in range(0, len(texts), _BATCH):
            batch = texts[i : i + _BATCH]
            resp = await client.post("/embeddings", json=_payload(batch), headers=_headers())
            resp.raise_for_status()
            out.extend(_parse(resp.json()))
    return out


async def embed_query(text: str) -> list[float]:
    result = await embed_texts([text])
    return result[0]
