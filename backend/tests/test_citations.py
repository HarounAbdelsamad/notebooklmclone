import uuid

from app.chat.orchestrator import _select_citations
from app.retrieval.hybrid import RetrievedChunk


def _sources(n: int) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content=f"source {i}",
            page_number=i,
            score=1.0 / (i + 1),
        )
        for i in range(n)
    ]


def test_select_citations_picks_referenced_markers():
    sources = _sources(3)
    answer = "The sky is blue [1] and grass is green [3]."
    picked = _select_citations(answer, sources)
    assert picked == [sources[0], sources[2]]


def test_select_citations_falls_back_to_all_when_none_referenced():
    sources = _sources(2)
    picked = _select_citations("No markers here.", sources)
    assert picked == sources


def test_select_citations_ignores_out_of_range_markers():
    sources = _sources(2)
    picked = _select_citations("Bad ref [9] and good [2].", sources)
    assert picked == [sources[1]]
