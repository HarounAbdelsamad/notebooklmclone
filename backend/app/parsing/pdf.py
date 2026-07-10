from app.models.enums import SourceType
from app.parsing.base import ParsedDocument, TextBlock, register


@register(SourceType.pdf)
class PdfParser:
    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument:
        import fitz  # PyMuPDF

        if data is None:
            raise ValueError("PDF parser requires file bytes")
        blocks: list[TextBlock] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            page_count = doc.page_count
            for i, page in enumerate(doc):
                text = page.get_text("text")
                if text and text.strip():
                    blocks.append(TextBlock(text=text, page_number=i + 1))
        return ParsedDocument(blocks=blocks, page_count=page_count, meta={"parser": "pymupdf"})
