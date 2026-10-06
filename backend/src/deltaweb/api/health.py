"""Health endpoints used by Kubernetes probes."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from deltaweb import __version__
from deltaweb.api.deps import SessionDep
from deltaweb.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(session: SessionDep) -> dict[str, str]:
    """Readiness: the app can serve traffic, which includes reaching the database."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready", "version": __version__, "environment": get_settings().environment}
