import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import OutputType, output_type_enum


class GeneratedOutput(UUIDPrimaryKey, TimestampMixin, Base):
    """LLM-generated artifacts for a notebook (summary, FAQ, study guide, briefing, timeline)."""

    __tablename__ = "generated_outputs"

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[OutputType] = mapped_column(output_type_enum, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("ix_generated_outputs_notebook_id", "notebook_id"),)
