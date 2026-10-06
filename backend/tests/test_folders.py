"""The folders table: a tree of folders owned by a user (needs Docker, see conftest.py)."""

import pytest
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deltaweb.models import Folder, User


@pytest.fixture
def owner(session: Session) -> User:
    user = User(email="owner@deltaweb.local")
    session.add(user)
    session.flush()
    return user


def test_migrations_created_the_folders_table(session: Session) -> None:
    assert "folders" in inspect(session.connection()).get_table_names()


def test_root_folder_has_no_parent(session: Session, owner: User) -> None:
    root = Folder(name="Research", owner_id=owner.id)
    session.add(root)
    session.flush()

    assert root.id is not None
    assert root.parent_id is None
    assert root.created_at is not None


def test_subfolder_points_to_its_parent(session: Session, owner: User) -> None:
    root = Folder(name="Research", owner_id=owner.id)
    session.add(root)
    session.flush()
    child = Folder(name="GF(2)", owner_id=owner.id, parent_id=root.id)
    session.add(child)
    session.flush()

    assert child.parent_id == root.id


def add(session: Session, name: str, owner: User, parent: Folder | None = None) -> Folder:
    folder = Folder(name=name, owner_id=owner.id, parent_id=parent.id if parent else None)
    session.add(folder)
    session.flush()
    return folder


def test_deleting_a_folder_deletes_its_subfolders(session: Session, owner: User) -> None:
    root = add(session, "Research", owner)
    child = add(session, "GF(2)", owner, root)
    add(session, "n=15", owner, child)
    other = add(session, "Teaching", owner)

    session.execute(delete(Folder).where(Folder.id == root.id))

    remaining = session.scalars(select(Folder.id)).all()
    assert remaining == [other.id]


@pytest.mark.parametrize("in_subfolder", [False, True])
def test_same_name_in_the_same_place_is_rejected(
    session: Session, owner: User, in_subfolder: bool
) -> None:
    parent = add(session, "Research", owner) if in_subfolder else None
    add(session, "GF(2)", owner, parent)

    with pytest.raises(IntegrityError):
        add(session, "GF(2)", owner, parent)
    session.rollback()


def test_names_are_case_sensitive(session: Session, owner: User) -> None:
    add(session, "Research", owner)
    add(session, "research", owner)
    add(session, "RESEARCH", owner)

    assert session.scalar(select(func.count()).select_from(Folder)) == 3


def test_same_name_is_allowed_in_different_places(session: Session, owner: User) -> None:
    first = add(session, "GF(2)", owner, add(session, "Research", owner))
    second = add(session, "GF(2)", owner, add(session, "Teaching", owner))
    other_user = User(email="other@deltaweb.local")
    session.add(other_user)
    session.flush()
    third = add(session, "GF(2)", other_user)

    assert len({first.id, second.id, third.id}) == 3


@pytest.mark.parametrize(
    "fields",
    [
        {"name": ""},  # empty name
        {"name": "Orphan", "owner_id": 999_999},  # owner does not exist
        {"name": "Lost", "parent_id": 999_999},  # parent does not exist
    ],
)
def test_invalid_folders_are_rejected(
    session: Session, owner: User, fields: dict[str, object]
) -> None:
    session.add(Folder(**{"owner_id": owner.id, **fields}))

    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
