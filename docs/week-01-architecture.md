# Week 1 architecture notes

Initial scaffolding decisions for `airesearcher`. See [`AGENTS.md`](../AGENTS.md) for the full, ongoing set of architecture decisions — this file covers just the Week 1 infra choices and their reasoning.

| Decision | Choice | Why |
|---|---|---|
| Monorepo layout | `apps/web`, `apps/api`, root `docker-compose.yml`, `docs/` | Two apps only — a `packages/` shared dir is premature until something real needs sharing |
| Web package manager | pnpm | Fast, disk-efficient, native workspace support if `packages/` is added later |
| Next.js | App Router + TypeScript + Tailwind CSS | Standard default; Tailwind pays off early for the eventual dashboard-heavy MVP UI |
| API dependency management | uv | Single tool for venv + deps + lockfile, fast installs in Docker builds |
| API structure | `routers/`, `core/`, `models/`, `schemas/` under `app/` | Standard scalable FastAPI layout |
| Postgres image | `pgvector/pgvector:pg16` (not plain `postgres`) | Avoids adding pgvector as a painful later migration once Week 3 (embeddings/hybrid search) lands |
| Migrations | Alembic (async SQLAlchemy 2.0) | Standard for FastAPI/SQLAlchemy; Week 1's only migration enables the `vector` and `pg_trgm` extensions — no feature tables yet |
| DB driver | `asyncpg` for the app, sync `psycopg` for Alembic | FastAPI is async end-to-end |
| Container orchestration | Docker Compose, 3 services (`postgres`, `api`, `web`), dev bind mounts | Local dev with hot reload |
| Basic UI | Landing page + client-side `StatusCard` hitting `/api/status` (which runs `SELECT 1` against Postgres) | Proves the full chain Next.js → FastAPI → Postgres end-to-end in one visible page |

## Verification checklist

1. `cp .env.example .env && docker compose up --build` — all three containers start; `postgres` and `api` report healthy
2. `curl http://localhost:8000/health` → `{"status":"ok"}`
3. `curl http://localhost:8000/api/status` → `{"api":"ok","db":"ok","timestamp":"..."}`
4. `http://localhost:3000` renders the landing page with green "API" and "Database" status badges
5. `docker compose exec postgres psql -U airesearcher -d airesearcher -c "\dx"` lists both `vector` and `pg_trgm`
6. `docker compose down && docker compose up` — data persists via the named volume
