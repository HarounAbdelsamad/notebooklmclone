"""Chunking strategies.

Primary: semantic chunking — sentences are embedded, boundaries placed where consecutive
sentences diverge (cosine distance above a threshold), then packed to a target token size
with configurable overlap. Falls back to recursive token chunking when no embedder is given
or embedding fails.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.config import settings
from app.parsing.base import TextBlock
from app.utils.text import split_sentences
from app.utils.tokenizer import count_tokens

EmbedFn = Callable[[list[str]], list[list[float]]]


@dataclass
class ChunkData:
    content: str
    chunk_index: int
    token_count: int
    page_number: int | None = None


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


def _pack_sentences(
    sentences: list[tuple[str, int | None]],
    target_tokens: int,
    overlap_ratio: float,
) -> list[ChunkData]:
    """Greedily pack (sentence, page) pairs into chunks near target_tokens with overlap."""
    chunks: list[ChunkData] = []
    overlap_tokens = int(target_tokens * overlap_ratio)
    current: list[tuple[str, int | None]] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        content = " ".join(s for s, _ in current).strip()
        pages = [p for _, p in current if p is not None]
        chunks.append(
            ChunkData(
                content=content,
                chunk_index=len(chunks),
                token_count=count_tokens(content),
                page_number=pages[0] if pages else None,
            )
        )
        # Seed the next chunk with a token-bounded tail for overlap.
        tail: list[tuple[str, int | None]] = []
        tail_tokens = 0
        for sent in reversed(current):
            t = count_tokens(sent[0])
            if tail_tokens + t > overlap_tokens:
                break
            tail.insert(0, sent)
            tail_tokens += t
        current = tail
        current_tokens = tail_tokens

    for sent, page in sentences:
        t = count_tokens(sent)
        if current_tokens + t > target_tokens and current:
            flush()
        current.append((sent, page))
        current_tokens += t
    flush()
    return chunks


def recursive_token_chunks(
    blocks: list[TextBlock],
    target_tokens: int | None = None,
    overlap_ratio: float | None = None,
) -> list[ChunkData]:
    target_tokens = target_tokens or settings.chunk_target_tokens
    overlap_ratio = settings.chunk_overlap_ratio if overlap_ratio is None else overlap_ratio
    sentences: list[tuple[str, int | None]] = []
    for block in blocks:
        for sent in split_sentences(block.text):
            sentences.append((sent, block.page_number))
    return _pack_sentences(sentences, target_tokens, overlap_ratio)


def semantic_chunks(
    blocks: list[TextBlock],
    embed_fn: EmbedFn | None,
    target_tokens: int | None = None,
    overlap_ratio: float | None = None,
    distance_percentile: float = 0.80,
) -> list[ChunkData]:
    target_tokens = target_tokens or settings.chunk_target_tokens
    overlap_ratio = settings.chunk_overlap_ratio if overlap_ratio is None else overlap_ratio

    sentences: list[tuple[str, int | None]] = []
    for block in blocks:
        for sent in split_sentences(block.text):
            sentences.append((sent, block.page_number))

    if embed_fn is None or len(sentences) < 4:
        return recursive_token_chunks(blocks, target_tokens, overlap_ratio)

    try:
        embeddings = embed_fn([s for s, _ in sentences])
    except Exception:
        return recursive_token_chunks(blocks, target_tokens, overlap_ratio)

    distances = [
        _cosine_distance(embeddings[i], embeddings[i + 1]) for i in range(len(embeddings) - 1)
    ]
    if not distances:
        return recursive_token_chunks(blocks, target_tokens, overlap_ratio)
    ordered = sorted(distances)
    threshold = ordered[min(int(len(ordered) * distance_percentile), len(ordered) - 1)]

    # Group sentences into semantic segments at high-divergence boundaries, then token-pack
    # each segment so no chunk exceeds the target size.
    chunks: list[ChunkData] = []
    segment: list[tuple[str, int | None]] = []
    for i, sent in enumerate(sentences):
        segment.append(sent)
        is_boundary = i < len(distances) and distances[i] >= threshold
        seg_tokens = sum(count_tokens(s) for s, _ in segment)
        if is_boundary or seg_tokens >= target_tokens:
            for packed in _pack_sentences(segment, target_tokens, overlap_ratio):
                packed.chunk_index = len(chunks)
                chunks.append(packed)
            segment = []
    if segment:
        for packed in _pack_sentences(segment, target_tokens, overlap_ratio):
            packed.chunk_index = len(chunks)
            chunks.append(packed)
    return chunks
