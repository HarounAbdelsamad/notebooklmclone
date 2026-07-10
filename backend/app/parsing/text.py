from app.models.enums import SourceType
from app.parsing.base import ParsedDocument, TextBlock, register


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


@register(SourceType.txt)
class TxtParser:
    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument:
        if data is None:
            raise ValueError("Text parser requires file bytes")
        return ParsedDocument(blocks=[TextBlock(text=_decode(data))], meta={"parser": "txt"})


@register(SourceType.markdown)
class MarkdownParser:
    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument:
        from markdown_it import MarkdownIt

        if data is None:
            raise ValueError("Markdown parser requires file bytes")
        raw = _decode(data)
        # Render to tokens then extract text content, preserving headings as paragraph breaks.
        md = MarkdownIt()
        tokens = md.parse(raw)
        parts: list[str] = []
        for tok in tokens:
            if tok.type == "inline" and tok.content:
                parts.append(tok.content)
        text = "\n\n".join(parts) if parts else raw
        return ParsedDocument(blocks=[TextBlock(text=text)], meta={"parser": "markdown-it"})
