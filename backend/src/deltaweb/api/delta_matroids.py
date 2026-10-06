"""Delta-matroids: compute without saving, and save, list, read, rename/move and delete."""

from concurrent.futures import Executor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deltaweb.api.deps import CurrentUser, SessionDep
from deltaweb.api.folders import get_own_folder
from deltaweb.config import get_settings
from deltaweb.domain.deltamatroid import DeltaMatroid, InvalidMatrixError
from deltaweb.models import DeltaMatroidRecord, User
from deltaweb.schemas.delta_matroid import (
    DeltaMatroidCreate,
    DeltaMatroidOut,
    DeltaMatroidSummary,
    DeltaMatroidUpdate,
    GeneratedDeltaMatroid,
    GenerateRequest,
)
from deltaweb.services.generation import GenerationResult, generate

router = APIRouter(prefix="/delta-matroids", tags=["delta-matroids"])


def get_executor(request: Request) -> Executor:
    """The worker pool created at startup (see ``lifespan`` in main.py)."""
    executor: Executor = request.app.state.executor
    return executor


ExecutorDep = Annotated[Executor, Depends(get_executor)]


def run_generation(executor: Executor, body: GenerateRequest) -> GenerationResult:
    """Generate in a worker process. Invalid matrix -> 422, too slow -> 503."""
    future = executor.submit(generate, body.matrix, body.field, body.labels)
    try:
        return future.result(timeout=get_settings().generation_timeout_seconds)
    except InvalidMatrixError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except FutureTimeoutError as exc:
        future.cancel()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Generation took too long, try again"
        ) from exc


def get_own_record(session: Session, user: User, record_id: int) -> DeltaMatroidRecord:
    """The delta-matroid, if it belongs to ``user``. Someone else's is 404, never 403."""
    record = session.scalar(
        select(DeltaMatroidRecord).where(
            DeltaMatroidRecord.id == record_id, DeltaMatroidRecord.owner_id == user.id
        )
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Delta-matroid not found")
    return record


def commit_or_conflict(session: Session) -> None:
    """Commit; the unique (owner, folder, name) constraint becomes a clean 409."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="A delta-matroid with that name already exists there"
        ) from exc


def to_out(record: DeltaMatroidRecord) -> DeltaMatroidOut:
    """Full view. Fingerprint and frequencies are recalculated from the stored family."""
    dm = DeltaMatroid(record.name, feasible_family=record.feasible, size=len(record.ground_set))
    field: Literal[2, 3] = 2 if record.field == 2 else 3
    return DeltaMatroidOut(
        id=record.id,
        name=record.name,
        folder_id=record.folder_id,
        field=field,
        matrix=record.matrix,
        ground_set=record.ground_set,
        feasible=record.feasible,
        fingerprint=list(dm.fingerprint),
        frequencies=dm.frequencies,
        created_at=record.created_at,
    )


@router.post("/generate")
def generate_delta_matroid(body: GenerateRequest, executor: ExecutorDep) -> GeneratedDeltaMatroid:
    """Delta-matroid of the non-singular principal submatrices over GF(field).

    Nothing is saved: this only computes. The work runs in a worker process.
    """
    result = run_generation(executor, body)
    return GeneratedDeltaMatroid(
        field=body.field,
        ground_set=result.ground_set,
        feasible=result.feasible,
        fingerprint=result.fingerprint,
        frequencies=result.frequencies,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_delta_matroid(
    body: DeltaMatroidCreate, session: SessionDep, user: CurrentUser, executor: ExecutorDep
) -> DeltaMatroidOut:
    """Generate from the matrix (in the worker pool) and save the result."""
    if body.folder_id is not None:
        get_own_folder(session, user, body.folder_id)
    result = run_generation(executor, body)
    record = DeltaMatroidRecord(
        name=body.name,
        owner_id=user.id,
        folder_id=body.folder_id,
        field=body.field,
        matrix=body.matrix,
        ground_set=result.ground_set,
        feasible=result.feasible,
    )
    session.add(record)
    commit_or_conflict(session)
    session.refresh(record)  # load created_at, set by the database
    return to_out(record)


@router.get("")
def list_delta_matroids(session: SessionDep, user: CurrentUser) -> list[DeltaMatroidSummary]:
    """Summaries of every delta-matroid of the user. Sizes are counted by the database,
    so the families are never loaded."""
    rows = session.execute(
        select(
            DeltaMatroidRecord.id,
            DeltaMatroidRecord.name,
            DeltaMatroidRecord.folder_id,
            DeltaMatroidRecord.field,
            func.cardinality(DeltaMatroidRecord.ground_set).label("size"),
            func.cardinality(DeltaMatroidRecord.feasible).label("feasible_count"),
            DeltaMatroidRecord.created_at,
        )
        .where(DeltaMatroidRecord.owner_id == user.id)
        .order_by(DeltaMatroidRecord.id)
    )
    return [DeltaMatroidSummary.model_validate(row._asdict()) for row in rows]


@router.get("/{record_id}")
def get_delta_matroid(record_id: int, session: SessionDep, user: CurrentUser) -> DeltaMatroidOut:
    return to_out(get_own_record(session, user, record_id))


@router.patch("/{record_id}")
def update_delta_matroid(
    record_id: int, body: DeltaMatroidUpdate, session: SessionDep, user: CurrentUser
) -> DeltaMatroidOut:
    record = get_own_record(session, user, record_id)
    if "folder_id" in body.model_fields_set:
        if body.folder_id is not None:
            get_own_folder(session, user, body.folder_id)
        record.folder_id = body.folder_id
    if body.name is not None:
        record.name = body.name
    commit_or_conflict(session)
    return to_out(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delta_matroid(record_id: int, session: SessionDep, user: CurrentUser) -> None:
    session.delete(get_own_record(session, user, record_id))
    session.commit()
