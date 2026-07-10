import uuid

from app.api import notes
from app.chat.orchestrator import _maintenance_due
from app.notes.embedding import note_embedding_text


def test_maintenance_not_due_within_recent_window():
    assert not _maintenance_due(2)
    assert not _maintenance_due(8)  # equal to recent window, not past it


def test_maintenance_due_on_interval_boundary():
    assert _maintenance_due(16)
    assert _maintenance_due(24)


def test_maintenance_not_due_off_boundary():
    assert not _maintenance_due(10)
    assert not _maintenance_due(14)


def test_note_embedding_text_combines_title_and_content():
    assert note_embedding_text("Title", "Body") == "Title\n\nBody"
    assert note_embedding_text("", "") == ""


def test_enqueue_note_embedding_calls_delay(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(notes.embed_note_task, "delay", lambda note_id: calls.append(note_id))
    nid = uuid.uuid4()
    notes._enqueue_note_embedding(nid)
    assert calls == [str(nid)]


def test_enqueue_note_embedding_swallows_broker_errors(monkeypatch):
    def boom(_note_id):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(notes.embed_note_task, "delay", boom)
    # Must not raise — enqueue failures are non-fatal to note create/update.
    notes._enqueue_note_embedding(uuid.uuid4())
