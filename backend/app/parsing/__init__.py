"""Parser package. Importing it registers every format parser in the registry."""

from app.parsing import (  # noqa: F401  (side-effect: registration)
    csv_parser,
    docx,
    html,
    pdf,
    pptx,
    text,
)
from app.parsing.base import ParsedDocument, Parser, TextBlock, get_parser

__all__ = ["ParsedDocument", "Parser", "TextBlock", "get_parser"]
