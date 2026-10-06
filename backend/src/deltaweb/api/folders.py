"""Folders of the current user: create, list, rename/move and delete."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deltaweb.api.deps import CurrentUser, SessionDep
from deltaweb.models import DeltaMatroidRecord, Folder, User
from deltaweb.schemas.folder import FolderCreate, FolderOut, FolderUpdate

router = APIRouter(prefix="/folders", tags=["folders"])


def get_own_folder(session: Session, user: User, folder_id: int) -> Folder:
    """The folder, if it belongs to ``user``. Someone else's folder is 404, never 403."""
    folder = session.scalar(
        select(Folder).where(Folder.id == folder_id, Folder.owner_id == user.id)
    )
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


def subtree_ids(session: Session, root_id: int) -> set[int]:
    """Ids of ``root_id`` and every folder below it, at any depth (recursive CTE)."""
    tree = select(Folder.id).where(Folder.id == root_id).cte("tree", recursive=True)
    tree = tree.union_all(select(Folder.id).where(Folder.parent_id == tree.c.id))
    return set(session.scalars(select(tree.c.id)))


def commit_or_conflict(session: Session) -> None:
    """Commit; the unique (owner, parent, name) constraint becomes a clean 409."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="A folder with that name already exists there"
        ) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
def create_folder(body: FolderCreate, session: SessionDep, user: CurrentUser) -> FolderOut:
    if body.parent_id is not None:
        get_own_folder(session, user, body.parent_id)
    folder = Folder(name=body.name, parent_id=body.parent_id, owner_id=user.id)
    session.add(folder)
    commit_or_conflict(session)
    session.refresh(folder)  # load created_at, set by the database
    return FolderOut.model_validate(folder)


@router.get("")
def list_folders(session: SessionDep, user: CurrentUser) -> list[FolderOut]:
    """Every folder of the user, at every level, as a flat list (build the tree from parent_id)."""
    folders = session.scalars(select(Folder).where(Folder.owner_id == user.id).order_by(Folder.id))
    return [FolderOut.model_validate(folder) for folder in folders]


@router.patch("/{folder_id}")
def update_folder(
    folder_id: int, body: FolderUpdate, session: SessionDep, user: CurrentUser
) -> FolderOut:
    folder = get_own_folder(session, user, folder_id)

    if "parent_id" in body.model_fields_set:
        if body.parent_id is not None:
            get_own_folder(session, user, body.parent_id)
            if body.parent_id in subtree_ids(session, folder.id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="A folder cannot be moved into itself or into one of its subfolders",
                )
        folder.parent_id = body.parent_id
    if body.name is not None:
        folder.name = body.name

    commit_or_conflict(session)
    return FolderOut.model_validate(folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int, session: SessionDep, user: CurrentUser, force: bool = False
) -> None:
    """Delete a folder and, with ``force=true``, everything inside it at every level:
    subfolders and delta-matroids (both through ON DELETE CASCADE)."""
    folder = get_own_folder(session, user, folder_id)
    tree = subtree_ids(session, folder.id)
    subfolders = len(tree) - 1
    delta_matroids = session.scalar(
        select(func.count())
        .select_from(DeltaMatroidRecord)
        .where(DeltaMatroidRecord.folder_id.in_(tree))
    )
    if (subfolders or delta_matroids) and not force:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": "The folder is not empty; repeat with force=true to delete everything",
                "subfolders": subfolders,
                "delta_matroids": delta_matroids,
            },
        )
    session.delete(folder)
    session.commit()
