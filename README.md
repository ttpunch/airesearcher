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
- API: http://localhost:8000
- API health check: http://localhost:8000/health
- Full-stack status (API + DB connectivity): http://localhost:8000/api/status

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
```

## Database migrations

Migrations run automatically on container start. To run them manually:

```bash
docker compose exec api uv run alembic upgrade head
```
