import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class Workspace(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "workspaces"

    # Clerk user id (owner). One user may own multiple workspaces.
    clerk_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="My Workspace")

    notebooks: Mapped[list["Notebook"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_workspaces_clerk_user_id", "clerk_user_id"),)


class Notebook(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "notebooks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="Untitled notebook")
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="notebooks")

    __table_args__ = (Index("ix_notebooks_workspace_id", "workspace_id"),)
