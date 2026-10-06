"""FastAPI application entry point.

Run locally with:  uv run fastapi dev src/deltaweb/main.py
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from deltaweb import __version__
from deltaweb.api import delta_matroids, folders, health
from deltaweb.config import get_settings
from deltaweb.services.generation import create_executor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the generation worker pool with the app and shut it down with it."""
    with create_executor(get_settings().generation_workers) as executor:
        app.state.executor = executor
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name, version=__version__, debug=settings.debug, lifespan=lifespan
    )
    app.include_router(health.router)
    app.include_router(folders.router)
    app.include_router(delta_matroids.router)
    return app


app = create_app()
