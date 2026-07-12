# Deploy your own NotebookLM clone

An ordered, top-to-bottom checklist to stand up your **own** instance from a fresh fork. Everything
uses your own accounts and secrets — none of it is baked into the repo. Deploy config lives in
`render.yaml` (API + Celery worker + Redis), `frontend/vercel.json`, and `.github/workflows/ci.yml`.

**Target stack:** React/Vite frontend on **Vercel** → FastAPI + Celery on **Render** → **Supabase**
Postgres (pgvector) + Storage. Auth via **Clerk**, LLM + embeddings + rerank via **OpenRouter**,
optional monitoring via **Sentry**.

> The API must run on a warm instance. `render.yaml` pins `plan: starter` because free-tier cold
> starts break SSE streaming. The Celery **worker is a separate Render service** from the API.

## Chicken-and-egg ordering

Two values only exist mid-way through, so provision in this order:

1. **Supabase** — DB + Storage, gather `DATABASE_URL` / `SUPABASE_*`.
2. **Clerk** — you need the publishable key (for Vercel) and JWKS/issuer (for Render) before either
   frontend or backend can verify auth.
3. **Render** — deploy the API/worker with a **placeholder** `CORS_ORIGINS` (you don't have the
   Vercel origin yet). Note the API URL.
4. **Vercel** — build the frontend with the real API URL + Clerk key. Note the resulting origin.
5. **Set real CORS** — put the Vercel origin into `CORS_ORIGINS` on Render, redeploy the API.
6. **Smoke test** end-to-end.

`CORS_ORIGINS` needs the Vercel origin, and the Vercel build needs the Clerk keys — that's the
"egg." The placeholder-then-fix loop in steps 3 and 5 breaks it.

---

## 0. Prerequisites

- A **GitHub fork/clone** of this repo — Render and Vercel both deploy from Git, so you need your own
  repo (referred to below as `<your-github-repo>`).
- Accounts: **Supabase**, **Render**, **Vercel**, **Clerk**, **OpenRouter** (and optionally
  **Sentry**).
- To run migrations locally (recommended once, to verify connectivity): Python 3.12 + the backend
  deps installed (`cd backend && pip install -e ".[dev]"`).

---

## 1. Supabase (database + storage)

1. Create a new Supabase project. Choose a region close to your Render region. Note its **project
   ref** (the `<project-ref>` in `https://<project-ref>.supabase.co`).
2. Enable pgvector — SQL Editor → run:
   ```sql
   create extension if not exists vector;
   ```
3. Create a Storage bucket named **`documents`** (must match `SUPABASE_STORAGE_BUCKET`). Keep it
   **private** — the backend uses the service-role key, so no public access is needed.
4. Apply the schema (see **§2**), then **enable Row-Level Security** on every app table. This closes
   the public anon/PostgREST surface. It is safe: the `postgres` role (used by `DATABASE_URL`) and
   `service_role` (used by Storage) both have `BYPASSRLS`, so the backend keeps full access while the
   anon key can read nothing. In the SQL Editor:
   ```sql
   alter table public.workspaces          enable row level security;
   alter table public.notebooks           enable row level security;
   alter table public.documents           enable row level security;
   alter table public.chunks              enable row level security;
   alter table public.chats               enable row level security;
   alter table public.messages            enable row level security;
   alter table public.message_citations   enable row level security;
   alter table public.chat_summaries      enable row level security;
   alter table public.chat_facts          enable row level security;
   alter table public.notes               enable row level security;
   alter table public.generated_outputs   enable row level security;
   alter table public.alembic_version     enable row level security;
   ```
   > Don't add policies — with no policies and RLS on, the anon role is fully denied, which is exactly
   > what you want. Verify names against `\dt public.*` (or the Table Editor) in case a table was
   > renamed in a later migration; the list above matches the `0001_baseline` schema.
5. Collect these values (never commit them):
   - **DATABASE_URL** — dashboard → **Connect** → **Session pooler**. Change the scheme so it reads
     `postgresql+asyncpg://<user>:<db-password>@<pooler-host>:5432/postgres`. See **§3** for why the
     pooler choice matters.
   - **SUPABASE_URL** — `https://<project-ref>.supabase.co`.
   - **SUPABASE_SERVICE_KEY** — Settings → API → **service_role** key (secret; never ship to the
     frontend).

## 2. Apply the schema (migrations)

From a machine with the backend deps installed, pointed at your Supabase DB:

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://<user>:<db-password>@<pooler-host>:5432/postgres" \
  python -m alembic upgrade head
```

This creates all tables, the `vector` extension objects, `VECTOR(1024)` columns, generated
`TSVECTOR` columns, and the HNSW + GIN indexes, and stamps `alembic_version` at `0001_baseline`.
Render also runs `alembic upgrade head` in the API build command, so this is optional — but running
it once locally confirms your `DATABASE_URL` actually reaches Supabase and that pgvector is enabled
**before** the first deploy.

## 3. DATABASE_URL — pick the right connection string

Use the Supabase **Session pooler** string (IPv4, port **5432**), scheme rewritten to
`postgresql+asyncpg://...`. Alembic derives the sync `+psycopg` URL automatically from this.

- **Do NOT** use the direct `db.<project-ref>.supabase.co` host — it is IPv6-only and often
  unreachable from Render.
- **Do NOT** use the **transaction** pooler (port **6543**) — it breaks asyncpg/psycopg prepared
  statements.

## 4. OpenRouter (LLM + embeddings + rerank)

Create one **OpenRouter API key**. This single `OPENROUTER_API_KEY` powers all three:

- the **LLM** (Llama 3.3),
- the **embeddings** (free NVIDIA Nemotron embed model), and
- the **rerank** (free NVIDIA Nemotron rerank model).

There is **no** separate DeepInfra / embeddings / rerank account. `EMBEDDINGS_API_KEY` /
`RERANK_API_KEY` are optional overrides — leave them unset unless you want to route embeddings/rerank
through a different provider.

## 5. Clerk (auth)

1. Create a Clerk application.
2. Note its **Frontend API URL** (e.g. `https://<your-subdomain>.clerk.accounts.dev`) and
   **publishable key** (`pk_test_...` in dev, `pk_live_...` in prod).
3. You'll set, on the **Render API** (step 6):
   - `CLERK_JWKS_URL` = `https://<your-subdomain>.clerk.accounts.dev/.well-known/jwks.json`
   - `CLERK_ISSUER`   = `https://<your-subdomain>.clerk.accounts.dev` (**required in production** —
     the backend refuses to verify tokens without it).
   - `CLERK_AUDIENCE` = **optional, leave it unset.** Clerk's default session tokens carry no `aud`
     claim, and the backend only enforces audience when this var is set. Only set it if you configure
     a Clerk JWT template with an audience.
4. The **publishable key** goes into Vercel (`VITE_CLERK_PUBLISHABLE_KEY`, step 7).

## 6. Render (API + worker + Redis) — via Blueprint

**You must deploy via the Blueprint** (`render.yaml`), not by hand-creating services. The Render
MCP/API cannot create a background **worker**, and the Celery worker is required for ingestion.

1. New → **Blueprint** → point at `<your-github-repo>`. Render reads `render.yaml` and proposes three
   services: `notebooklm-api` (web), `notebooklm-worker`, `notebooklm-redis`. `REDIS_URL` is
   auto-wired between them, and `ENVIRONMENT=production` is baked in (this is what disables the dev
   auth-bypass and the local-storage fallback).
2. Set each `sync: false` secret. The worker needs the subset marked below:

   | Env var                | API | Worker | Value source                                 |
   | ---------------------- | :-: | :----: | -------------------------------------------- |
   | `DATABASE_URL`         |  ✓  |   ✓    | §1/§3 (async asyncpg session-pooler form)    |
   | `SUPABASE_URL`         |  ✓  |   ✓    | §1                                           |
   | `SUPABASE_SERVICE_KEY` |  ✓  |   ✓    | §1                                           |
   | `OPENROUTER_API_KEY`   |  ✓  |   ✓    | §4 (also powers embeddings + rerank)         |
   | `CLERK_JWKS_URL`       |  ✓  |        | §5                                           |
   | `CLERK_ISSUER`         |  ✓  |        | §5 (required in prod)                        |
   | `CLERK_AUDIENCE`       |     |        | §5 (optional — leave unset)                  |
   | `CORS_ORIGINS`         |  ✓  |        | §8 — set a **placeholder** now, fix after §7 |
   | `SENTRY_DSN`           |  ✓  |        | §9 (optional)                                |

   Non-secret vars are already in `render.yaml` (`ENVIRONMENT`, `SUPABASE_STORAGE_BUCKET=documents`,
   `MAX_UPLOAD_MB=25`, `PYTHON_VERSION`, `REDIS_URL`).

   > Embeddings + rerank reuse `OPENROUTER_API_KEY` (§4). The optional `EMBEDDINGS_API_KEY` /
   > `RERANK_API_KEY` overrides are not part of the blueprint; leave them unset.

   For `CORS_ORIGINS`, put any placeholder for now (e.g. `https://<your-app>.vercel.app`) — you'll set
   the real origin in §8 once Vercel gives you one.
3. Deploy. Wait for the API health check at `/api/health` to go green.
4. Note the **API URL**: `https://<your-api>.onrender.com`.

## 7. Vercel (frontend)

1. New Vercel project → import `<your-github-repo>`. Set **Root Directory** to `frontend/`.
   `frontend/vercel.json` handles the Vite build + SPA rewrites.
2. Set env vars (Production):
   - `VITE_API_BASE_URL` = `https://<your-api>.onrender.com/api` — **include the `/api` suffix.**
   - `VITE_CLERK_PUBLISHABLE_KEY` = your Clerk publishable key (§5).
   - `VITE_SENTRY_DSN` = frontend Sentry DSN (optional; §9).
3. Deploy. Copy the resulting origin, e.g. `https://<your-app>.vercel.app`.

## 8. CORS (finish the loop)

Set `CORS_ORIGINS` on the Render **API** service to the **exact** Vercel origin from §7, with **no
trailing slash** (e.g. `https://<your-app>.vercel.app`). Comma-separate multiple origins (e.g. a
custom domain). **Redeploy the API** for the change to take effect.

> Browsers cache CORS preflight responses (~10 min). If you tested before this step, a stale
> preflight can linger — do a fresh/incognito load to clear it before concluding CORS is still broken.

## 9. Sentry (optional)

- Backend: create a project, put its DSN in `SENTRY_DSN` on the Render **API** service.
- Frontend: create a project, put its DSN in `VITE_SENTRY_DSN` on Vercel.

## 10. Keep-warm (defense-in-depth)

The starter plan already prevents cold starts; add an external pinger as a safety net (chosen over a
Render cron service to keep the blueprint simple / avoid another paid worker):

- Create a monitor on a free uptime service (UptimeRobot, cron-job.org, BetterStack, …).
- Target: `https://<your-api>.onrender.com/api/health`
- Interval: every **10 minutes**, method GET, expect HTTP 200.

## 11. GitHub Actions deploy hooks (optional)

CI (`.github/workflows/ci.yml`) auto-deploys on push to `main` **after** the backend + frontend jobs
pass. Add these repo secrets (Settings → Secrets and variables → Actions):

- `RENDER_DEPLOY_HOOK_URL` — Render API service → Settings → Deploy Hook URL. (Each Blueprint service
  can have its own hook; add a separate one for the worker if you want it redeployed too.)
- `VERCEL_DEPLOY_HOOK_URL` — **optional.** If Vercel's Git integration already auto-deploys on push
  to `main`, leave this unset and the CI step no-ops. Set it only if you disabled auto-deploy.

Both steps skip gracefully when their secret is absent — never hardcode hook URLs.

## 12. End-to-end smoke test

1. Open your Vercel URL and **sign in** via Clerk.
2. **Create a notebook**, then **upload** a PDF or `.txt`.
3. Watch the document reach **ready** status (Celery ingestion: extract → clean → chunk → embed →
   store). If it stalls, check the Render **worker** logs and Redis connectivity.
4. **Ask** a question grounded in the document.
5. Confirm a **streamed** answer (SSE) arrives **with citations** `[n]` mapping to source
   chunks/pages. If the stream stalls, check the Render **API** logs for the chat path.

If any step fails, check: Render API logs, Render worker logs, Supabase logs, and Sentry. A
code/config bug in the app (not infra) should be routed to the `backend` / `frontend` agents.
