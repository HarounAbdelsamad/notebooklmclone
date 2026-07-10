import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MessageRole
from app.schemas.common import IdentifiedModel


class ChatCreate(BaseModel):
    title: str = Field(default="New chat", max_length=500)


class ChatOut(IdentifiedModel):
    notebook_id: uuid.UUID
    title: str


class CitationOut(BaseModel):
    chunk_id: uuid.UUID | None
    document_id: uuid.UUID | None
    snippet: str | None
    page_number: int | None
    score: float | None
    rank: int | None


class MessageOut(IdentifiedModel):
    chat_id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[CitationOut] = []


class AskRequest(BaseModel):
    """Ask a question in a chat; the answer streams back over SSE."""

    question: str = Field(min_length=1)
    chat_id: uuid.UUID | None = None  # None => start a new chat


class ChatDetail(ChatOut):
    updated_at: datetime
    messages: list[MessageOut] = []
