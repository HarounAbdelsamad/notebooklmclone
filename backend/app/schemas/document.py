import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DocumentStatus, SourceType
from app.schemas.common import IdentifiedModel


class DocumentOut(IdentifiedModel):
    notebook_id: uuid.UUID
    filename: str
    source_type: SourceType
    mime_type: str | None
    source_url: str | None
    status: DocumentStatus
    error: str | None
    page_count: int | None
    char_count: int | None
    processed_at: datetime | None


class UploadInitRequest(BaseModel):
    """Request a signed URL to upload a file directly to storage."""

    filename: str = Field(max_length=1024)
    source_type: SourceType
    mime_type: str | None = None


class UploadInitResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    storage_path: str


class UrlIngestRequest(BaseModel):
    """Ingest a web page / URL source (no file upload)."""

    url: str = Field(max_length=2048)
    source_type: SourceType = SourceType.url
    title: str | None = None
