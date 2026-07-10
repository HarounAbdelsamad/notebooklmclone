"""FastAPI auth dependencies: authenticate the Clerk user and resolve their workspace."""

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import verify_token
from app.config import settings
from app.db.session import get_db
from app.models.workspace import Workspace

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    clerk_user_id: str
    claims: dict


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_dev_user: str | None = Header(default=None, alias="X-Dev-User"),
) -> Principal:
    """Authenticate the caller from the ``Authorization: Bearer <jwt>`` header.

    Dev escape hatch: when running outside production with Clerk unconfigured, an
    ``X-Dev-User`` header is accepted as the user id so the stack can be exercised
    end-to-end without a live Clerk tenant. Never active in production.
    """
    if not settings.is_production and not settings.clerk_jwks_url and x_dev_user:
        return Principal(clerk_user_id=x_dev_user, claims={"sub": x_dev_user, "dev": True})

    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = verify_token(creds.credentials)
    except Exception as exc:  # noqa: BLE001 — any verification failure is a 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return Principal(clerk_user_id=claims["sub"], claims=claims)


async def get_current_workspace(
    principal: Principal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Return the caller's default workspace, creating one on first access."""
    result = await db.execute(
        select(Workspace)
        .where(Workspace.clerk_user_id == principal.clerk_user_id)
        .order_by(Workspace.created_at.asc())
        .limit(1)
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(clerk_user_id=principal.clerk_user_id, name="My Workspace")
        db.add(workspace)
        await db.flush()
    return workspace
