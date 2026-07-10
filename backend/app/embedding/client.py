"""bge-m3 embeddings via a DeepInfra OpenAI-compatible ``/embeddings`` endpoint.

bge-m3 is multilingual and produces 1024-dim vectors; queries and passages use the same
model. Batches are sent in one request. Sync + async variants are provided because the
Celery ingestion pipeline needs a sync embedder for semantic chunking.
"""

import httpx

from app.config import settings

_BATCH = 64


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.embeddings_api_key}"}


def _payload(texts: list[str]) -> dict:
    return {"model": settings.embedding_model, "input": texts}


def _parse(data: dict) -> list[list[float]]:
    # OpenAI-compatible response: {"data": [{"embedding": [...], "index": i}, ...]}
    items = sorted(data["data"], key=lambda d: d.get("index", 0))
    return [item["embedding"] for item in items]


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
