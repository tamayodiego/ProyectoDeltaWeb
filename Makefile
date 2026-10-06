# Atajos del proyecto. `make` o `make help` muestra la lista.

.DEFAULT_GOAL := help
.PHONY: help install hooks db db-down db-logs db-shell migrate migration backend frontend test lint format build

help: ## Muestra esta ayuda
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias del backend y del frontend
	cd backend && uv sync
	cd frontend && pnpm install

hooks: ## Activa pre-commit en este repo (una sola vez)
	uv tool install pre-commit
	pre-commit install

db: ## Levanta PostgreSQL local (Docker Compose)
	docker compose up -d --wait db

db-down: ## Apaga PostgreSQL (los datos se conservan en el volumen)
	docker compose down

db-logs: ## Muestra los logs de PostgreSQL
	docker compose logs -f db

db-shell: ## Abre psql dentro del contenedor
	docker compose exec db psql -U delta -d delta_dev

migrate: ## Aplica las migraciones pendientes a la base local
	cd backend && uv run alembic upgrade head

migration: ## Crea una migración desde los modelos: make migration m="create folders"
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

backend: ## Corre la API en modo desarrollo (http://127.0.0.1:8000/docs)
	cd backend && uv run fastapi dev src/deltaweb/main.py

frontend: ## Corre el frontend en modo desarrollo
	cd frontend && pnpm dev

test: ## Corre las pruebas del backend (las de BD necesitan Docker encendido)
	cd backend && uv run pytest

lint: ## Revisa estilo y tipos (Ruff, mypy, ESLint)
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd frontend && pnpm lint

format: ## Formatea el código del backend
	cd backend && uv run ruff format . && uv run ruff check --fix .

build: ## Construye las imágenes Docker de backend y frontend
	docker build -t deltaweb-backend ./backend
	docker build -t deltaweb-frontend ./frontend
