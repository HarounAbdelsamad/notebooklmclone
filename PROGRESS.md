# Project Progress

Status snapshot for the NotebookLM clone. See `CLAUDE.md` for architecture, commands, and
conventions. Full build plan lives at `~/.claude/plans/this-is-a-new-precious-puddle.md`.

**Overall:** Phases 0–4 complete and verified. All four pre-deploy security findings are fixed.
Phase 5 deployment **config + docs** are done; the actual cloud **provisioning is manual** (needs
your accounts/secrets) and is the only thing between here and a live end-to-end run.

---

## ✅ Done

### Phase 0 — Scaffold & infra
- Monorepo layout (`backend/`, `frontend/`), `docker-compose.yml` (Postgres+pgvector, Redis),
  `.env.example` for both stacks, `.gitignore`, GitHub Actions CI (`.github/workflows/ci.yml`),
  backend `pyproject.toml` (ruff + pytest).

### Phase 1 — Auth + data model + CRUD
- **Auth:** Clerk JWKS verification (`app/auth/clerk.py`) + `get_current_user` / workspace
  resolution (`app/auth/deps.py`), plus a non-prod `X-Dev-User` bypass.
- **Data model:** all 11 tables as SQLAlchemy models with a hand-written Alembic baseline
  (`0001_baseline.py`): `vector` extension, enum types, `VECTOR(1024)` columns, generated
  `TSVECTOR` columns, HNSW + GIN indexes.
- **CRUD API + frontend shell:** notebooks/documents/notes routers; React app with Clerk auth,
  notebook list, and the 3-column workspace.

### Phase 2 — Upload + ingestion
- Storage (`app/services/storage.py`) with Supabase + local `./uploads` dev fallback.
- Celery + Redis wiring; ingestion pipeline (`app/ingestion/pipeline.py`):
  `extract → clean → semantic-chunk (20% overlap) → embed → store` with per-stage status.
- 8 format parsers; semantic chunker with recursive fallback; bge-m3 embeddings. Frontend upload +
  processing-status polling.

### Phase 3 — RAG chat + streaming + citations
- Hybrid retrieval = pgvector ⊕ Postgres FTS via **RRF** + bge-reranker (`app/retrieval/hybrid.py`).
- Query rewrite + context assembly in `app/chat/orchestrator.py` / `app/chat/memory.py`;
  OpenRouter streaming (`app/services/llm.py`).
- SSE event contract (`start → token* → citations → done` / `error`); citation persistence +
  clickable chips in the chat UI.
- Unified cross-content search (`app/retrieval/search.py` + `app/api/search.py`) and generated
  outputs (`app/outputs/generator.py`).

### Phase 4 — Memory, note embeddings ✅ (now wired)
- **Chat memory auto-triggers** — `stream_answer` now enqueues `summarize_chat` + `extract_chat_facts`
  (`app/chat/orchestrator.py` → `_schedule_memory_maintenance`) after a turn once the chat exceeds
  the recent window (`RECENT_MESSAGE_LIMIT = 8`), on an 8-message interval boundary (fires ~once per
  4 turns, never per-message; enqueue failures are swallowed).
- **Note embeddings** — notes are embedded on create/update via a new `embed_note` Celery task
  (`app/notes/embedding.py`, `app/workers/tasks.py`, enqueued from `app/api/notes.py`). `hybrid.py`
  gained `_note_vector_search`, fusing note vectors into the RRF pool + rerank, so notes now
  participate in chat retrieval (previously only FTS search surfaced them).
- Contract note (non-breaking): note-sourced citations carry `chunk_id: null` / `document_id: null`.
  `CitationOut` already declared both nullable, and the frontend chip renders them fine as `[n]`
  (no page). Deep-linking to a note would need a new `note_id` on the citation → schema + `types.ts`
  change (deferred, see Optional stretch).

### Security — all four pre-deploy findings fixed ✅
1. **Stored XSS** — `SearchPanel.tsx` no longer uses `dangerouslySetInnerHTML`. A `HighlightedSnippet`
   component splits on the backend's `<mark>`/`</mark>` delimiters and renders highlighted segments as
   real `<mark>` elements, everything else as auto-escaped React text nodes.
2. **SSRF** — `app/parsing/html.py` `UrlParser` now goes through `app/utils/net.py` `safe_get`:
   http(s)-only, DNS-resolves and blocks loopback/private/link-local/reserved/unspecified/multicast
   (covers `169.254.169.254`), re-validates every redirect hop, and normalizes IPv4-mapped/6to4 IPv6
   so `::ffff:169.254.169.254`-style literals can't bypass on Python 3.12.
3. **Unbounded upload** — `app/api/documents.py` reads via `read_upload_capped` (`app/utils/uploads.py`),
   a bounded chunked read that aborts with HTTP 413; cap = `MAX_UPLOAD_MB` (default 25). Content-Length
   is a pre-check only; the streamed byte count is authoritative.
4. **Auth hardening** — `X-Dev-User` confirmed inert whenever `ENVIRONMENT=production` or `CLERK_JWKS_URL`
   is set. `clerk.py` fails closed in production if `CLERK_ISSUER`/`CLERK_AUDIENCE` are unset, and requires
   the `iss`/`aud` claims whenever configured.

### Phase 5 — Deploy config + docs ✅ (provisioning still manual)
- `render.yaml` — API web + Celery worker + Redis (all `plan: starter` to avoid SSE-breaking cold
  starts). Added `ENVIRONMENT=production` (this is what disables the dev auth-bypass and local-storage
  fallback in prod), `CLERK_AUDIENCE`, `MAX_UPLOAD_MB`, `SUPABASE_STORAGE_BUCKET`.
- `.github/workflows/ci.yml` — new `deploy` job (push-to-`main`, after tests+build), secret-guarded
  Render deploy hook; Vercel left to its Git integration.
- `.env.example` (backend + frontend) fully documented; `DEPLOY.md` runbook written with the ordered
  manual provisioning checklist.
- Keep-warm: external uptime-pinger approach documented in `DEPLOY.md` (chosen over a paid cron service).

### Verified (in this environment, all changes together)
| Check | Result |
| --- | --- |
| Backend tests (`pytest`) | ✅ 42 pass (40 + IPv4-mapped SSRF cases) |
| Ruff lint + format | ✅ clean (82 files) |
| Backend imports & boots | ✅ `app.main` imports |
| Frontend `vite build` | ✅ 152 modules |
| Frontend `eslint` | ✅ clean |
| YAML/JSON configs | ✅ render.yaml / ci.yml / vercel.json valid |

---

## 📝 Manual steps for you (before live e2e — see `DEPLOY.md` for exact commands)

These need your own accounts/secrets and create real (billable) cloud resources, so they were left
for you rather than run automatically:

1. **Supabase** — create project; enable the `vector` extension; create the `documents` storage
   bucket; collect `DATABASE_URL` (asyncpg form), service key.
2. **Migrate** — run `alembic upgrade head` against Supabase (`DEPLOY.md` §2).
3. **Render** — create a Blueprint from `render.yaml`; set every `sync:false` secret on both the API
   and worker services.
4. **Vercel** — new project rooted at `frontend/`; set the `VITE_` env vars (Clerk publishable key,
   API base URL, optional Sentry DSN); deploy. Then set `CORS_ORIGINS` on the Render API to the
   resulting Vercel origin.
5. **Clerk** — configure JWKS URL, issuer, and audience (issuer + audience are **required** in prod;
   the backend now refuses to verify tokens without them).
6. **Sentry** — set backend `SENTRY_DSN` (Render) and frontend `VITE_SENTRY_DSN` (Vercel).
7. **GitHub Actions secrets** — `RENDER_DEPLOY_HOOK_URL` (and optionally `VERCEL_DEPLOY_HOOK_URL`).
8. **Keep-warm** — point an uptime pinger at `/api/health` (`DEPLOY.md` §4).
9. **Smoke test** — upload → processed → ask → cited answer (`DEPLOY.md` §9).

MCP note: the **Supabase** and **Vercel** connectors are available if you want me to drive some of
the above interactively, but **Google Drive** and **Hugging Face** connectors are currently
unauthorized (authorize them in claude.ai connector settings if needed — not required for this deploy).

---

## ⏳ Remaining / optional

### Residual hardening (low priority for a short-lived demo)
- **SSRF DNS-rebinding (TOCTOU)** — `validate_public_url` resolves and blocks, but the subsequent
  `httpx` GET re-resolves independently, so a hostile DNS server could return a public IP at
  validation and a private IP at fetch. Fully closing this needs connection pinning to the validated
  IP. Mitigated for the multi-record case (any internal record → reject); acceptable residual for now.

### Optional stretch
- Expose chat summaries/facts in the UI.
- Note-citation deep-linking: add `note_id` to `CitationOut` (schema + `types.ts` change + migration
  if persisted) so note-sourced citations can jump to the note.
- Full PDF viewer with citation jump-to-page.
- Additional formats: images/OCR, audio/Whisper, YouTube transcript, epub.

### Not yet run: live end-to-end
The upload → ready → ask → cited answer flow still hasn't been exercised against a real DB — it's
gated on the manual provisioning above (needs Supabase + Redis + API keys).
