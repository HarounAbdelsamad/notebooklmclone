from app.parsing.base import TextBlock
from app.utils.chunking import recursive_token_chunks, semantic_chunks


def _sample_blocks() -> list[TextBlock]:
    text = " ".join(f"This is sentence number {i} about topic alpha." for i in range(40))
    return [TextBlock(text=text, page_number=1)]


def test_recursive_chunks_respect_target_and_overlap():
    chunks = recursive_token_chunks(_sample_blocks(), target_tokens=60, overlap_ratio=0.2)
    assert len(chunks) > 1
    assert all(c.token_count <= 90 for c in chunks)  # target + overlap headroom
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.page_number == 1 for c in chunks)


def test_semantic_falls_back_without_embedder():
    # No embed_fn => recursive fallback, still produces valid chunks.
    chunks = semantic_chunks(_sample_blocks(), embed_fn=None, target_tokens=60)
    assert len(chunks) >= 1
    assert all(c.content for c in chunks)


def test_semantic_with_stub_embedder():
    def fake_embed(texts: list[str]) -> list[list[float]]:
        # Two clusters: first half topic A, second half topic B.
        return [[1.0, 0.0] if i < len(texts) // 2 else [0.0, 1.0] for i in range(len(texts))]

    chunks = semantic_chunks(_sample_blocks(), embed_fn=fake_embed, target_tokens=200)
    assert len(chunks) >= 1
