.PHONY: up down logs migrate lint test

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api uv run alembic upgrade head

lint:
	cd apps/web && pnpm lint
	cd apps/api && uv run ruff check .

test:
	docker compose exec api uv run pytest
