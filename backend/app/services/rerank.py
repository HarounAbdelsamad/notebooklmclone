"""Reranking via bge-reranker-v2-m3 on DeepInfra.

Returns a relevance score per document (higher = more relevant). On any failure it raises;
callers fall back to the pre-rerank ordering so retrieval still works without the reranker.
"""

import httpx

from app.config import settings


async def rerank(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    url = f"{settings.rerank_base_url.rstrip('/')}/{settings.rerank_model}"
    payload = {"queries": [query] * len(documents), "documents": documents}
    headers = {"Authorization": f"Bearer {settings.rerank_api_key}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    # DeepInfra returns {"scores": [...]}; be tolerant of alternate shapes.
    if isinstance(data, dict) and "scores" in data:
        return [float(s) for s in data["scores"]]
    if isinstance(data, list):
        return [float(s) for s in data]
    raise ValueError(f"Unexpected rerank response shape: {type(data)}")
