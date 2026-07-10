import uuid

from pydantic import BaseModel

from app.models.enums import OutputType
from app.schemas.common import IdentifiedModel


class OutputGenerateRequest(BaseModel):
    type: OutputType
    title: str | None = None
    params: dict | None = None


class OutputOut(IdentifiedModel):
    notebook_id: uuid.UUID
    type: OutputType
    title: str
    content: str
    params: dict | None
