from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_notebook
from app.db.session import get_db
from app.models.workspace import Notebook
from app.retrieval.search import unified_search
from app.schemas.search import SearchResponse, SearchScope

router = APIRouter(prefix="/notebooks/{notebook_id}/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    scopes: list[SearchScope] = Query(default=list(SearchScope)),
    limit: int = Query(default=20, le=100),
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Full-text search across documents, notes, and chats within a notebook."""
    hits = await unified_search(db=db, notebook_id=notebook.id, query=q, scopes=scopes, limit=limit)
    return SearchResponse(query=q, hits=hits)
