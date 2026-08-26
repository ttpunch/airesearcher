# airesearcher

A BHEL (Bharat Heavy Electricals Limited) public-data-first AI research and intelligence platform.

See [`AGENTS.md`](AGENTS.md) for the architecture decisions, roadmap, and constraints, and [`docs/research/bhel-ai-strategy.html`](docs/research/bhel-ai-strategy.html) for the full strategy report this project is built from.

## Prerequisites

- Docker + Docker Compose v2
- (Optional, for local non-Docker dev) Node 22, [pnpm](https://pnpm.io), Python 3.12, [uv](https://docs.astral.sh/uv/)

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000 ([docs](http://localhost:8000/docs))
- API health check: http://localhost:8000/health
- Full-stack status (API + DB connectivity): http://localhost:8000/api/status
- MinIO console (object storage): http://localhost:9001 (login from `.env`'s `S3_ACCESS_KEY`/`S3_SECRET_KEY`)

On startup the API seeds the source registry with BHEL's known Tier-1 URLs — `GET /api/sources` should show them immediately.

## Working with documents and search

```
POST /api/sources/{id}/crawl        # fetch a registered source's URL
POST /api/documents/upload          # upload a PDF directly (multipart "file")
POST /api/documents/{id}/process    # chunk + embed a document's extracted text
GET  /api/search?q=...&alpha=0.5    # hybrid (vector + text) search with citations
```

Set `VOYAGE_API_KEY` in `.env` for real embeddings (Voyage AI). Without it, the API falls back to a deterministic but **not semantically meaningful** local embedder — the pipeline runs end-to-end, but search *ranking quality* requires a real key. See `app/core/embeddings.py`.

## Asking the research assistant

```
POST /api/ask   {"question": "..."}
```

Runs the agentic research loop (Claude Agent SDK): it searches indexed documents, cites every factual claim as `[chunk:<id>]`, labels claims FACT/INFERENCE/RECOMMENDATION, and says "I cannot verify this from public sources" when the evidence doesn't support an answer. The response's `verified` field is only `true` when every citation was checked against what the agent actually retrieved. Try it in the browser at http://localhost:3000/ask.

Requires `ANTHROPIC_API_KEY` (or another Claude Agent SDK-supported credential) in the API's environment — the endpoint calls the real SDK, unlike the automated tests, which stub it out (see `app/agent/research_agent.py`'s module docstring for why).

## Project structure

```
apps/
  web/    Next.js frontend (App Router, TypeScript, Tailwind)
  api/    FastAPI backend (uv, SQLAlchemy 2.0 async, Alembic)
docs/
  research/   The BHEL AI strategy report this project implements
  week-01-architecture.md   Architecture decisions for the initial scaffold
docker-compose.yml
```

## Common commands

```bash
make up        # docker compose up --build
make down      # docker compose down
make logs      # tail logs from all services
make migrate   # run Alembic migrations manually
make lint      # lint both apps
make test      # run the API test suite
```

## Database migrations

Migrations run automatically on container start. To run them manually:

```bash
docker compose exec api uv run alembic upgrade head
```
