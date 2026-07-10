"""Unit tests for the OpenRouter-backed embedding + rerank clients (HTTP fully mocked)."""

import math

import httpx
import pytest

from app.config import settings
from app.embedding import client as embed_client
from app.services import rerank as rerank_service


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_embedding_truncates_2048_to_1024_unit_norm(monkeypatch):
    # A 2048-dim raw vector should be sliced to embedding_dim and L2-normalized.
    raw = [float(i % 7 + 1) for i in range(2048)]
    payload = {"data": [{"embedding": raw, "index": 0}]}

    async def fake_post(self, *args, **kwargs):
        return _FakeResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    import asyncio

    vec = asyncio.run(embed_client.embed_query("hello"))

    assert len(vec) == settings.embedding_dim == 1024
    norm = math.sqrt(sum(x * x for x in vec))
    assert norm == pytest.approx(1.0, abs=1e-6)
    # Direction preserved: first component equals raw[0]/norm(raw[:1024]).
    expected_norm = math.sqrt(sum(x * x for x in raw[:1024]))
    assert vec[0] == pytest.approx(raw[0] / expected_norm, abs=1e-9)


def test_embedding_raises_when_shorter_than_pinned_dim():
    with pytest.raises(ValueError):
        embed_client._to_pinned_dim([0.1] * 512)


def test_rerank_remaps_out_of_order_results(monkeypatch):
    documents = ["doc0", "doc1", "doc2"]
    # Endpoint returns results sorted by relevance, NOT in input order.
    payload = {
        "results": [
            {"index": 2, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.5},
            {"index": 1, "relevance_score": 0.1},
        ]
    }

    async def fake_post(self, *args, **kwargs):
        return _FakeResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    import asyncio

    scores = asyncio.run(rerank_service.rerank("q", documents))

    assert scores == [0.5, 0.1, 0.9]  # aligned back to input order


def test_rerank_empty_documents_short_circuits():
    import asyncio

    assert asyncio.run(rerank_service.rerank("q", [])) == []
