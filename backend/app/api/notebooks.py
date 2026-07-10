from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_notebook
from app.auth.deps import get_current_workspace
from app.db.session import get_db
from app.models.chat import Chat
from app.models.document import Document
from app.models.note import Note
from app.models.workspace import Notebook, Workspace
from app.schemas.notebook import (
    NotebookCreate,
    NotebookDetail,
    NotebookOut,
    NotebookUpdate,
)

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


@router.get("", response_model=list[NotebookOut])
async def list_notebooks(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> list[Notebook]:
    result = await db.execute(
        select(Notebook)
        .where(Notebook.workspace_id == workspace.id)
        .order_by(Notebook.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    payload: NotebookCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> Notebook:
    notebook = Notebook(
        workspace_id=workspace.id,
        title=payload.title,
        description=payload.description,
    )
    db.add(notebook)
    await db.flush()
    return notebook


@router.get("/{notebook_id}", response_model=NotebookDetail)
async def get_notebook(
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> NotebookDetail:
    counts = {}
    for key, model in (
        ("document_count", Document),
        ("note_count", Note),
        ("chat_count", Chat),
    ):
        result = await db.execute(
            select(func.count()).select_from(model).where(model.notebook_id == notebook.id)
        )
        counts[key] = result.scalar_one()
    return NotebookDetail.model_validate(notebook).model_copy(update=counts)


@router.patch("/{notebook_id}", response_model=NotebookOut)
async def update_notebook(
    payload: NotebookUpdate,
    notebook: Notebook = Depends(get_owned_notebook),
) -> Notebook:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(notebook, field, value)
    return notebook


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.delete(notebook)
