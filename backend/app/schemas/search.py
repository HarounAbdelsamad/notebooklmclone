import uuid
from enum import Enum

from pydantic import BaseModel


class SearchScope(str, Enum):
    documents = "documents"
    notes = "notes"
    chats = "chats"


class SearchHit(BaseModel):
    scope: SearchScope
    id: uuid.UUID
    title: str | None
    snippet: str
    score: float
    notebook_id: uuid.UUID
    document_id: uuid.UUID | None = None
    page_number: int | None = None


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
