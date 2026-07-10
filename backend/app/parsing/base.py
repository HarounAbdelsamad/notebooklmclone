"""Parser abstractions: a registry mapping SourceType -> parser, and shared value types."""

from dataclasses import dataclass, field
from typing import Protocol

from app.models.enums import SourceType


@dataclass
class TextBlock:
    """A contiguous span of extracted text with optional page provenance."""

    text: str
    page_number: int | None = None


@dataclass
class ParsedDocument:
    blocks: list[TextBlock] = field(default_factory=list)
    page_count: int | None = None
    meta: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks if b.text.strip())

    @property
    def char_count(self) -> int:
        return sum(len(b.text) for b in self.blocks)


class Parser(Protocol):
    """A parser turns raw bytes (or a URL) into a ParsedDocument."""

    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument: ...


_REGISTRY: dict[SourceType, "Parser"] = {}


def register(source_type: SourceType):
    def decorator(cls):
        _REGISTRY[source_type] = cls()
        return cls

    return decorator


def get_parser(source_type: SourceType) -> "Parser":
    if source_type not in _REGISTRY:
        raise ValueError(f"No parser registered for source_type={source_type.value}")
    return _REGISTRY[source_type]
