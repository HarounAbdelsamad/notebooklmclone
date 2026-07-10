import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import NoteSource
from app.schemas.common import IdentifiedModel


class NoteCreate(BaseModel):
    title: str = Field(default="Untitled note", max_length=500)
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    content: str | None = None


class NoteOut(IdentifiedModel):
    notebook_id: uuid.UUID
    title: str
    content: str
    source: NoteSource
    updated_at: datetime
