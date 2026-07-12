# NotebookLM Clone

A NotebookLM-style app: upload documents into notebooks and chat with them via grounded,
cited RAG — plus notes, generated outputs, and cross-content search.

## Architecture

| Layer            | Choice                                                            |
| ---------------- | ----------------------------------------------------------------- |
| Frontend         | React + Vite + TypeScript (Vercel)                                |
| Auth             | Clerk                                                             |
| Backend          | FastAPI + SSE streaming (Render)                                  |
| Background queue | Celery + Redis                                                    |
| DB / vectors     | Supabase Postgres + pgvector                                      |
| File storage     | Supabase Storage                                                  |
| LLM              | OpenRouter (open models: Llama 3.3 / Qwen 2.5)                    |
| Embeddings       | `nvidia/llama-nemotron-embed-vl-1b-v2` (2048-d → truncated 1024) via OpenRouter |
| Rerank           | `nvidia/llama-nemotron-rerank-vl-1b-v2` via OpenRouter            |
| Monitoring       | Sentry                                                            |

### RAG pipeline
`question → query rewrite → embed → hybrid retrieval (pgvector ⊕ Postgres FTS via RRF) →
rerank → context assembly (summary + facts + recent + retrieved) → LLM (SSE) → answer + citations`

### Ingestion pipeline (Celery)
`upload → extract → clean → semantic-chunk (20% overlap) → embed → store → ready`

Supported formats (MVP): pdf, docx, txt, markdown, html, website URL, ppt, csv.

## Repository layout
```
backend/    FastAPI app, Celery workers, SQLAlchemy models, Alembic migrations
frontend/   Vite + React + TypeScript SPA
docker-compose.yml   Local Postgres(pgvector) + Redis
```

## Local development

### 1. Infra
```bash
docker compose up -d          # Postgres (pgvector) + Redis
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env          # fill in Clerk / Supabase / API keys
alembic upgrade head
uvicorn app.main:app --reload
# In a second terminal — the Celery worker:
celery -A app.workers.celery_app.celery worker --loglevel=info
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local    # fill in Clerk publishable key + API URL
npm run dev
```

See [backend/.env.example](backend/.env.example) and [frontend/.env.example](frontend/.env.example)
for required secrets.

## Deploy your own

The app runs on a fully managed stack: **Vercel** (frontend) + **Render** (FastAPI API + Celery
worker + Redis) + **Supabase** (Postgres/pgvector + Storage) + **Clerk** (auth) + **OpenRouter**
(LLM + embeddings + rerank), with optional **Sentry** monitoring.

Follow [`DEPLOY.md`](DEPLOY.md) — an ordered, reproducible checklist (Supabase → Clerk → Render →
Vercel → CORS → smoke test) that provisions everything from a fresh fork using your own accounts and
secrets.
