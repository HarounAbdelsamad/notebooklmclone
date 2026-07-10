"""Reranking via ``nvidia/llama-nemotron-rerank-vl-1b-v2:free`` through OpenRouter's Cohere-style
``/rerank`` endpoint.

Returns one relevance score per input document (higher = more relevant), aligned to the ORIGINAL
``documents`` order. The endpoint returns results sorted by score descending, so we remap each
result back to its input index. On any failure it raises; callers fall back to the pre-rerank
ordering so retrieval still works without the reranker.
"""

import httpx

from app.config import settings


async def rerank(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    url = f"{settings.rerank_base_url.rstrip('/')}/rerank"
    payload = {"model": settings.rerank_model, "query": query, "documents": documents}
    headers = {"Authorization": f"Bearer {settings.effective_rerank_api_key}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Primary shape: {"results": [{"index": i, "relevance_score": s}, ...]} sorted by score desc.
    if isinstance(data, dict) and "results" in data:
        scores = [0.0] * len(documents)
        for r in data["results"]:
            idx = int(r["index"])
            score = r.get("relevance_score", r.get("score"))
            scores[idx] = float(score)
        return scores
    # Legacy already-aligned shape: {"scores": [...]}.
    if isinstance(data, dict) and "scores" in data:
        return [float(s) for s in data["scores"]]
    # Bare list of already-aligned scores.
    if isinstance(data, list):
        return [float(s) for s in data]
    raise ValueError(f"Unexpected rerank response shape: {type(data)}")
