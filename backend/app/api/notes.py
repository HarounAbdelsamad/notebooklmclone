import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_notebook
from app.db.session import get_db
from app.models.enums import NoteSource
from app.models.note import Note
from app.models.workspace import Notebook
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate
from app.workers.tasks import embed_note as embed_note_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notebooks/{notebook_id}/notes", tags=["notes"])


def _enqueue_note_embedding(note_id: uuid.UUID) -> None:
    """Queue a background (re)embed of a note. Never raises — a queue failure must not break
    note create/update."""
    try:
        embed_note_task.delay(str(note_id))
    except Exception:  # noqa: BLE001 — best-effort enqueue
        logger.warning("Failed to enqueue note embedding for %s", note_id, exc_info=True)


@router.get("", response_model=list[NoteOut])
async def list_notes(
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> list[Note]:
    result = await db.execute(
        select(Note).where(Note.notebook_id == notebook.id).order_by(Note.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> Note:
    note = Note(
        notebook_id=notebook.id,
        title=payload.title,
        content=payload.content,
        source=NoteSource.user,
    )
    db.add(note)
    # Commit before enqueue so the worker (separate process) can read the row by id.
    await db.commit()
    _enqueue_note_embedding(note.id)
    return note


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> Note:
    note = await _get_owned_note(note_id, notebook, db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(note, field, value)
    await db.commit()
    # Title/content changed => the embedding is stale; refresh it in the background.
    if updates:
        _enqueue_note_embedding(note.id)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> None:
    note = await _get_owned_note(note_id, notebook, db)
    await db.delete(note)


async def _get_owned_note(note_id: uuid.UUID, notebook: Notebook, db: AsyncSession) -> Note:
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.notebook_id == notebook.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note
