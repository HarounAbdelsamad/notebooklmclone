"""Import all models so Base.metadata is fully populated (Alembic + create_all)."""

from app.models.chat import (
    Chat,
    ChatFact,
    ChatSummary,
    Message,
    MessageCitation,
)
from app.models.document import Chunk, Document
from app.models.enums import (
    DocumentStatus,
    MessageRole,
    NoteSource,
    OutputType,
    SourceType,
)
from app.models.note import Note
from app.models.output import GeneratedOutput
from app.models.workspace import Notebook, Workspace

__all__ = [
    "Workspace",
    "Notebook",
    "Document",
    "Chunk",
    "Chat",
    "Message",
    "MessageCitation",
    "ChatSummary",
    "ChatFact",
    "Note",
    "GeneratedOutput",
    "SourceType",
    "DocumentStatus",
    "MessageRole",
    "NoteSource",
    "OutputType",
]
