# Backend

FastAPI + Python 3.12, managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                   # create .venv and install dependencies
uv run fastapi dev src/deltaweb/main.py   # dev server at http://127.0.0.1:8000 (docs at /docs)
uv run pytest                             # tests
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

## Layout

```
src/deltaweb/
├── main.py       # create_app(): builds the FastAPI app
├── config.py     # settings from DELTAWEB_* environment variables
├── api/          # routers (HTTP endpoints)
├── schemas/      # Pydantic request/response models
├── services/     # use cases: API <-> domain <-> database
└── domain/       # pure delta-matroid logic (Phase 1)
tests/
```
