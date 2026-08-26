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

Runs the agentic research loop: it searches indexed documents, cites every factual claim as `[chunk:<id>]`, labels claims FACT/INFERENCE/RECOMMENDATION, and says "I cannot verify this from public sources" when the evidence doesn't support an answer. The response's `verified` field is only `true` when every citation was checked against what the agent actually retrieved. Try it in the browser at http://localhost:3000/ask.

### Model provider

Set `LLM_PROVIDER` in `.env` to pick which model runs the loop:

| `LLM_PROVIDER` | Backend | Required key |
|---|---|---|
| `anthropic` (default) | Claude Agent SDK — the primary, most-tested path (see AGENTS.md for why) | `ANTHROPIC_API_KEY` |
| `openrouter` | Hand-rolled tool-calling loop against OpenRouter's OpenAI-compatible API — `OPENROUTER_MODEL` can be any model OpenRouter serves, not just DeepSeek's | `OPENROUTER_API_KEY` |
| `deepseek` | Same loop against DeepSeek's API directly | `DEEPSEEK_API_KEY` |

All three use the exact same tools and evidence-discipline system prompt (`app/agent/openai_compatible.py` for the latter two) — same citation verification either way, just a different model behind it. Whichever one is active, the endpoint calls the real API, unlike the automated tests, which stub it out (see `app/agent/research_agent.py`'s module docstring for why).

## Tender intelligence

```
GET  /api/tenders?status=open&organization=BHEL   # list, optionally filtered
GET  /api/tenders/{id}
POST /api/tenders                                  # register a tender
POST /api/tenders/{id}/extract                      # deterministic field extraction from its linked document
GET  /api/tenders/analyze                           # counts by status and organization
```

Extraction is regex-based, not an LLM call — a field only appears if it was actually found in the document text (closing date, EMD amount, tender ref, eligibility-clause sentences). Browse it at http://localhost:3000/tenders.

Also seeded on startup: `https://gem.gov.in/` (Government e-Marketplace, India's central procurement portal) as a T1 tender-portal source, plus two real BHEL bid records found there (`GEM/2022/B/2650225`, `GEM/2023/B/3489664`) — title/ref/url are real, closing date and value are left null since they weren't independently verifiable. GeM isn't auto-crawled (its bid search is a dynamic, session-based page, not something the simple GET-based crawler can meaningfully scrape) — add more via `POST /api/tenders` or PDF upload.

## Knowledge graph: competitors and technologies

```
GET  /api/entities?entity_type=competitor   # or technology, organization
GET  /api/entities/{id}                     # includes its relationships
POST /api/entities
```

On startup the API also seeds BHEL, four competitors (L&T Power, Siemens Energy, GE Vernova, Thermax — each linked to their real official site, verified live), and four technology concepts (Digital Twin, Agentic AI, GraphRAG, IIoT), plus `competes_with`/`relevant_to` relationships between them. Browse at http://localhost:3000/competitors and http://localhost:3000/technologies.

## Deep Research

```
POST /api/research   {"topic": "..."}
GET  /api/research
GET  /api/research/{id}
```

Generalizes `/api/ask` into a topic-level report: the agent searches indexed documents, tenders, *and* KG entities together, citing each claim as `[chunk:<id>]`, `[tender:<id>]`, or `[entity:<id>]` — verified the same way as `/api/ask` (only counted if actually retrieved via a tool call this turn). Reports persist and are listed on http://localhost:3000/research. Same `LLM_PROVIDER` options as `/api/ask` above.

## Opportunities, knowledge graph, and dashboard

```
GET  /api/opportunities?status=proposed
GET  /api/opportunities/{id}
POST /api/opportunities/{id}/approve   {"approved_by": "..."}
POST /api/opportunities/{id}/reject    {"approved_by": "..."}
GET  /api/relationships
GET  /api/dashboard/summary
```

`/api/opportunities` is seeded on startup with the strategy report's real Top 10 Strategic Initiatives and their weighted ROI scores — every one starts `status="proposed"` and only changes via an explicit approve/reject call (RECOMMENDATION-tagged output requires human approval; see AGENTS.md). `approved_by` is a plain name field, not real authentication. Browse and decide on them at http://localhost:3000/opportunities, browse the knowledge graph at http://localhost:3000/graph, and get an overview of everything indexed at http://localhost:3000/dashboard.

## All pages

| Page | What it shows |
|---|---|
| `/` | Landing page, nav, system status |
| `/dashboard` | Aggregate counts across every table + top opportunities |
| `/ask` | Single-question Q&A with citation-verified answers |
| `/research` | Multi-source-class Deep Research reports |
| `/tenders` | Tender list, bid-pattern summary |
| `/competitors` | Seeded competitor entities with links to their real sites |
| `/technologies` | Seeded technology concept entities |
| `/opportunities` | Top 10 initiatives, with approve/reject |
| `/graph` | Entities by type + relationships table |

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
