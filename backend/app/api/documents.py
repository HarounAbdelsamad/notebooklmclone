import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_notebook
from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus, SourceType
from app.models.workspace import Notebook
from app.schemas.document import DocumentOut, UrlIngestRequest
from app.services.storage import build_storage_path, upload_bytes
from app.workers.tasks import ingest_document

router = APIRouter(prefix="/notebooks/{notebook_id}/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.notebook_id == notebook.id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    notebook: Notebook = Depends(get_owned_notebook),
    file: UploadFile = File(...),
    source_type: SourceType = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Document:
    """Upload a file, persist it to object storage, and queue ingestion."""
    data = await file.read()
    storage_path = build_storage_path(notebook.id, file.filename or "upload")
    await upload_bytes(storage_path, data, content_type=file.content_type)

    document = Document(
        notebook_id=notebook.id,
        filename=file.filename or "upload",
        source_type=source_type,
        mime_type=file.content_type,
        storage_path=storage_path,
        status=DocumentStatus.queued,
    )
    db.add(document)
    # Commit before enqueue so the worker (separate process) can read the row by id.
    await db.commit()
    ingest_document.delay(str(document.id))
    return document


@router.post("/url", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def ingest_url(
    payload: UrlIngestRequest,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> Document:
    document = Document(
        notebook_id=notebook.id,
        filename=payload.title or payload.url,
        source_type=payload.source_type,
        source_url=payload.url,
        status=DocumentStatus.queued,
    )
    db.add(document)
    await db.commit()
    ingest_document.delay(str(document.id))
    return document


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> Document:
    document = await _get_owned_document(document_id, notebook, db)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> None:
    document = await _get_owned_document(document_id, notebook, db)
    await db.delete(document)


async def _get_owned_document(
    document_id: uuid.UUID, notebook: Notebook, db: AsyncSession
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.notebook_id == notebook.id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
