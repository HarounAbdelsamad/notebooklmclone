"""Shared API dependencies: resolve and authorize notebook-scoped resources."""

import uuid

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Notebook, Workspace


async def get_owned_notebook(
    notebook_id: uuid.UUID = Path(...),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> Notebook:
    """Fetch a notebook and assert it belongs to the caller's workspace (else 404)."""
    result = await db.execute(
        select(Notebook).where(
            Notebook.id == notebook_id,
            Notebook.workspace_id == workspace.id,
        )
    )
    notebook = result.scalar_one_or_none()
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    return notebook
