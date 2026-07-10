from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedModel


class NotebookCreate(BaseModel):
    title: str = Field(default="Untitled notebook", max_length=500)
    description: str | None = Field(default=None, max_length=2000)


class NotebookUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)


class NotebookOut(IdentifiedModel):
    title: str
    description: str | None
    updated_at: datetime


class NotebookDetail(NotebookOut):
    document_count: int = 0
    note_count: int = 0
    chat_count: int = 0
