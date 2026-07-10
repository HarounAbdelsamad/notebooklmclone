"""Celery tasks. Each wraps an async pipeline function via ``asyncio.run``.

Note: ``asyncio.run`` creates a fresh event loop per task, and the DB engine is created
lazily per process (see app.db.session), so no loop-affinity issues arise across tasks.
"""

import asyncio

from app.workers.celery_app import celery


@celery.task(name="ingest_document", bind=True, max_retries=2, default_retry_delay=10)
def ingest_document(self, document_id: str) -> None:
    from app.ingestion.pipeline import run_ingestion

    asyncio.run(run_ingestion(document_id))


@celery.task(name="generate_output")
def generate_output(output_id: str) -> None:
    from app.outputs.generator import run_generate_output

    asyncio.run(run_generate_output(output_id))


@celery.task(name="summarize_chat")
def summarize_chat(chat_id: str) -> None:
    from app.chat.maintenance import summarize_chat as _summarize

    asyncio.run(_summarize(chat_id))


@celery.task(name="extract_chat_facts")
def extract_chat_facts(chat_id: str) -> None:
    from app.chat.maintenance import extract_facts

    asyncio.run(extract_facts(chat_id))
