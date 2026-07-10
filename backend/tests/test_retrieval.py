import uuid
from dataclasses import dataclass

from app.retrieval.hybrid import _rrf_fuse


@dataclass
class FakeChunk:
    id: uuid.UUID


def test_rrf_fuse_ranks_items_appearing_in_both_lists_higher():
    a, b, c = (FakeChunk(uuid.uuid4()) for _ in range(3))
    vector_list = [a, b, c]
    fts_list = [c, a]  # c and a appear in both; b only once
    fused = _rrf_fuse(vector_list, fts_list)
    ids = [x.id for x in fused]
    # a is top of one list and 2nd of the other => should outrank b (single appearance).
    assert ids.index(a.id) < ids.index(b.id)
    assert set(ids) == {a.id, b.id, c.id}


def test_rrf_fuse_dedupes():
    a = FakeChunk(uuid.uuid4())
    fused = _rrf_fuse([a], [a], [a])
    assert len(fused) == 1
