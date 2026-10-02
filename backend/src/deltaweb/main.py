"""FastAPI application entry point.

Run locally with:  uv run fastapi dev src/deltaweb/main.py
"""

from fastapi import FastAPI

from deltaweb import __version__
from deltaweb.api import health
from deltaweb.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__, debug=settings.debug)
    app.include_router(health.router)
    return app


app = create_app()
