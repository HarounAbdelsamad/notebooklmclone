"""baseline schema — workspaces, notebooks, documents/chunks, chats/messages/memory, notes, outputs

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Embedding dimension is pinned to bge-m3's 1024. Changing the embedding model to a
# different dimension requires a new migration + re-embed of all chunks/notes.
EMBED_DIM = 1024


def _uuid_pk() -> sa.Column:
    # Fresh Column per table — a Column instance can only belong to one table.
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def _enum(name: str) -> postgresql.ENUM:
    # References an enum type created via raw DDL below; does not re-create it.
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        "CREATE TYPE source_type AS ENUM ('pdf','docx','txt','markdown','html','url','ppt','csv')"
    )
    op.execute(
        "CREATE TYPE document_status AS ENUM "
        "('queued','extracting','cleaning','chunking','embedding','ready','failed')"
    )
    op.execute("CREATE TYPE message_role AS ENUM ('user','assistant','system')")
    op.execute("CREATE TYPE note_source AS ENUM ('user','generated')")
    op.execute(
        "CREATE TYPE output_type AS ENUM ('summary','faq','study_guide','briefing','timeline')"
    )

    # ---- workspaces ----
    op.create_table(
        "workspaces",
        _uuid_pk(),
        sa.Column("clerk_user_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default="My Workspace"),
        *_timestamps(),
    )
    op.create_index("ix_workspaces_clerk_user_id", "workspaces", ["clerk_user_id"])

    # ---- notebooks ----
    op.create_table(
        "notebooks",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False, server_default="Untitled notebook"),
        sa.Column("description", sa.String(2000), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_notebooks_workspace_id", "notebooks", ["workspace_id"])

    # ---- documents ----
    op.create_table(
        "documents",
        _uuid_pk(),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(1024), nullable=False),
        sa.Column("source_type", _enum("source_type"), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("storage_path", sa.String(2048), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("status", _enum("document_status"), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_documents_notebook_id", "documents", ["notebook_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # ---- chunks ----
    op.create_table(
        "chunks",
        _uuid_pk(),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBED_DIM), nullable=True),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
        ),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_notebook_id", "chunks", ["notebook_id"])
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # ---- chats ----
    op.create_table(
        "chats",
        _uuid_pk(),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False, server_default="New chat"),
        *_timestamps(),
    )
    op.create_index("ix_chats_notebook_id", "chats", ["notebook_id"])

    # ---- messages ----
    op.create_table(
        "messages",
        _uuid_pk(),
        sa.Column(
            "chat_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", _enum("message_role"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
        ),
        *_timestamps(),
    )
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"])
    op.create_index("ix_messages_tsv", "messages", ["tsv"], postgresql_using="gin")

    # ---- message_citations ----
    op.create_table(
        "message_citations",
        _uuid_pk(),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_message_citations_message_id", "message_citations", ["message_id"])

    # ---- chat_summaries ----
    op.create_table(
        "chat_summaries",
        _uuid_pk(),
        sa.Column(
            "chat_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column(
            "up_to_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )
    op.create_index("ix_chat_summaries_chat_id", "chat_summaries", ["chat_id"])

    # ---- chat_facts ----
    op.create_table(
        "chat_facts",
        _uuid_pk(),
        sa.Column(
            "chat_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_text", sa.Text(), nullable=False),
        sa.Column(
            "source_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )
    op.create_index("ix_chat_facts_chat_id", "chat_facts", ["chat_id"])

    # ---- notes ----
    op.create_table(
        "notes",
        _uuid_pk(),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False, server_default="Untitled note"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", _enum("note_source"), nullable=False, server_default="user"),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBED_DIM), nullable=True),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title,'') || ' ' || content)",
                persisted=True,
            ),
        ),
        *_timestamps(),
    )
    op.create_index("ix_notes_notebook_id", "notes", ["notebook_id"])
    op.create_index("ix_notes_tsv", "notes", ["tsv"], postgresql_using="gin")

    # ---- generated_outputs ----
    op.create_table(
        "generated_outputs",
        _uuid_pk(),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", _enum("output_type"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("params", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_generated_outputs_notebook_id", "generated_outputs", ["notebook_id"])


def downgrade() -> None:
    for table in (
        "generated_outputs",
        "notes",
        "chat_facts",
        "chat_summaries",
        "message_citations",
        "messages",
        "chats",
        "chunks",
        "documents",
        "notebooks",
        "workspaces",
    ):
        op.drop_table(table)

    for enum_name in (
        "output_type",
        "note_source",
        "message_role",
        "document_status",
        "source_type",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
