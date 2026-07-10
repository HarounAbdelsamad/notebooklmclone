import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import NoteSource, note_source_enum


class Note(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "notes"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="Untitled note")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[NoteSource] = mapped_column(
        note_source_enum, nullable=False, default=NoteSource.user
    )

    # Notes are embeddable so they participate in cross-content search / retrieval.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(title,'') || ' ' || content)", persisted=True),
    )

    __table_args__ = (
        Index("ix_notes_notebook_id", "notebook_id"),
        Index("ix_notes_tsv", "tsv", postgresql_using="gin"),
    )
