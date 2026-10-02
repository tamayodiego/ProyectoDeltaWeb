"""Health endpoints used by Kubernetes probes."""

from fastapi import APIRouter

from deltaweb import __version__
from deltaweb.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    """Readiness: the app can serve traffic (later: also checks the database)."""
    return {"status": "ready", "version": __version__, "environment": get_settings().environment}
