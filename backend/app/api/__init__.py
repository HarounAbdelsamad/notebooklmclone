from fastapi import APIRouter

from app.api import chat, documents, health, notebooks, notes, outputs, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(notebooks.router)
api_router.include_router(documents.router)
api_router.include_router(notes.router)
api_router.include_router(chat.router)
api_router.include_router(search.router)
api_router.include_router(outputs.router)

__all__ = ["api_router"]
