"""Enumerations shared across models, plus their SQLAlchemy native-enum type objects.

The type objects carry explicit snake_case names and ``create_type=False`` so the Alembic
baseline migration owns creation of the Postgres enum types (avoids double-create). Columns
store the enum ``.value`` (lowercase strings) via ``values_callable``.
"""

import enum

from sqlalchemy import Enum as SAEnum


class SourceType(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"
    markdown = "markdown"
    html = "html"
    url = "url"
    ppt = "ppt"
    csv = "csv"
    # Post-MVP: image, audio, youtube, epub


class DocumentStatus(str, enum.Enum):
    queued = "queued"
    extracting = "extracting"
    cleaning = "cleaning"
    chunking = "chunking"
    embedding = "embedding"
    ready = "ready"
    failed = "failed"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class NoteSource(str, enum.Enum):
    user = "user"
    generated = "generated"


class OutputType(str, enum.Enum):
    summary = "summary"
    faq = "faq"
    study_guide = "study_guide"
    briefing = "briefing"
    timeline = "timeline"


def _pg_enum(py_enum: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(
        py_enum,
        name=name,
        native_enum=True,
        create_type=False,  # created explicitly in the baseline migration
        values_callable=lambda e: [m.value for m in e],
    )


source_type_enum = _pg_enum(SourceType, "source_type")
document_status_enum = _pg_enum(DocumentStatus, "document_status")
message_role_enum = _pg_enum(MessageRole, "message_role")
note_source_enum = _pg_enum(NoteSource, "note_source")
output_type_enum = _pg_enum(OutputType, "output_type")
