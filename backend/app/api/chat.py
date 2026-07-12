import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_owned_notebook
from app.chat.orchestrator import stream_answer
from app.db.session import get_db
from app.models.chat import Chat, Message
from app.models.workspace import Notebook
from app.schemas.chat import AskRequest, ChatCreate, ChatDetail, ChatOut

router = APIRouter(prefix="/notebooks/{notebook_id}/chats", tags=["chat"])


@router.get("", response_model=list[ChatOut])
async def list_chats(
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> list[Chat]:
    result = await db.execute(
        select(Chat).where(Chat.notebook_id == notebook.id).order_by(Chat.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ChatCreate,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> Chat:
    chat = Chat(notebook_id=notebook.id, title=payload.title)
    db.add(chat)
    await db.flush()
    return chat


@router.get("/{chat_id}", response_model=ChatDetail)
async def get_chat(
    chat_id: uuid.UUID,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> Chat:
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.notebook_id == notebook.id)
        .options(selectinload(Chat.messages).selectinload(Message.citations))
    )
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


@router.post("/ask")
async def ask(
    payload: AskRequest,
    notebook: Notebook = Depends(get_owned_notebook),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Run the RAG pipeline and stream the answer over SSE.

    Emits events: ``token`` (partial text), ``citations`` (JSON array), ``done``
    (``{chat_id, message_id}``), and ``error``.
    """
    return EventSourceResponse(
        stream_answer(
            db=db,
            notebook=notebook,
            chat_id=payload.chat_id,
            question=payload.question,
        ),
        # sse-starlette defaults to "\r\n" separators, but the frontend SSE parser splits events
        # on "\n\n" — emit "\n"-delimited events so event boundaries are actually detected.
        sep="\n",
    )
