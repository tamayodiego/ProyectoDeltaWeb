"""Delta-matroid computations."""

from concurrent.futures import Executor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from deltaweb.config import get_settings
from deltaweb.domain.deltamatroid import InvalidMatrixError
from deltaweb.schemas.delta_matroid import GeneratedDeltaMatroid, GenerateRequest
from deltaweb.services.generation import generate

router = APIRouter(prefix="/delta-matroids", tags=["delta-matroids"])


def get_executor(request: Request) -> Executor:
    """The worker pool created at startup (see ``lifespan`` in main.py)."""
    executor: Executor = request.app.state.executor
    return executor


ExecutorDep = Annotated[Executor, Depends(get_executor)]


@router.post("/generate")
def generate_delta_matroid(body: GenerateRequest, executor: ExecutorDep) -> GeneratedDeltaMatroid:
    """Delta-matroid of the non-singular principal submatrices over GF(field).

    Nothing is saved: this only computes. The work runs in a worker process.
    """
    future = executor.submit(generate, body.matrix, body.field, body.labels)
    try:
        result = future.result(timeout=get_settings().generation_timeout_seconds)
    except InvalidMatrixError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except FutureTimeoutError as exc:
        future.cancel()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Generation took too long, try again"
        ) from exc
    return GeneratedDeltaMatroid(
        field=body.field,
        ground_set=result.ground_set,
        feasible=result.feasible,
        fingerprint=result.fingerprint,
        frequencies=result.frequencies,
    )
