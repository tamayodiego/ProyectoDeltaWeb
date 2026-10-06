"""Tests for the folders API (Phase 2a). Needs Docker (see conftest.py).

Expected API, in ``src/deltaweb/api/folders.py`` (router included in ``main.py``) with
schemas in ``src/deltaweb/schemas/folder.py``:

    POST   /folders          body {"name", "parent_id"?}           -> 201 FolderOut
    GET    /folders                                                 -> 200 list[FolderOut]
    PATCH  /folders/{id}     body {"name"?, "parent_id"?}           -> 200 FolderOut
    DELETE /folders/{id}     ?force=true to delete a non-empty one  -> 204

FolderOut = {"id", "name", "parent_id", "created_at"}

Rules:
- Every user only sees their own folders. Someone else's folder answers 404, never 403.
- Names: surrounding spaces are stripped; empty or blank -> 422; max 255 characters.
- Same name in the same place -> 409 (the database rejects it; turn that into a clean error).
- PATCH: a field that is not sent is not changed; "parent_id": null moves to the root.
- PATCH: moving a folder into itself or into one of its descendants -> 400.
- DELETE without force on a folder with subfolders -> 409 with
  ``detail["subfolders"]`` = number of subfolders at every level; nothing is deleted.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from deltaweb.models import Folder, User


def create(client: TestClient, name: str, parent_id: int | None = None) -> dict:
    response = client.post("/folders", json={"name": name, "parent_id": parent_id})
    assert response.status_code == 201, response.text
    return response.json()


def names(client: TestClient) -> set[str]:
    return {folder["name"] for folder in client.get("/folders").json()}


@pytest.fixture
def foreign_folder(session: Session) -> Folder:
    """A folder that belongs to another user."""
    other = User(email="other@deltaweb.local")
    session.add(other)
    session.flush()
    folder = Folder(name="Not yours", owner_id=other.id)
    session.add(folder)
    session.flush()
    return folder


# --- POST /folders ---


def test_create_root_folder(client: TestClient) -> None:
    folder = create(client, "Research")

    assert folder["name"] == "Research"
    assert folder["parent_id"] is None
    assert isinstance(folder["id"], int)
    assert "created_at" in folder


def test_create_subfolder(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])

    assert child["parent_id"] == root["id"]


def test_name_is_stripped(client: TestClient) -> None:
    assert create(client, "  Research  ")["name"] == "Research"


@pytest.mark.parametrize("name", ["", "   ", "x" * 256])
def test_invalid_name_is_rejected(client: TestClient, name: str) -> None:
    response = client.post("/folders", json={"name": name})

    assert response.status_code == 422


def test_duplicate_name_in_the_same_place_is_a_conflict(client: TestClient) -> None:
    create(client, "Research")

    response = client.post("/folders", json={"name": "Research"})

    assert response.status_code == 409


def test_unknown_parent_is_not_found(client: TestClient) -> None:
    response = client.post("/folders", json={"name": "Lost", "parent_id": 999_999})

    assert response.status_code == 404


def test_parent_of_another_user_is_not_found(client: TestClient, foreign_folder: Folder) -> None:
    response = client.post("/folders", json={"name": "Sneaky", "parent_id": foreign_folder.id})

    assert response.status_code == 404


# --- GET /folders ---


def test_list_returns_every_level_flat(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])
    create(client, "n=15", child["id"])

    assert names(client) == {"Research", "GF(2)", "n=15"}


def test_list_hides_folders_of_other_users(client: TestClient, foreign_folder: Folder) -> None:
    create(client, "Mine")

    assert names(client) == {"Mine"}


# --- PATCH /folders/{id} ---


def test_rename_keeps_the_parent(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])

    response = client.patch(f"/folders/{child['id']}", json={"name": "GF(3)"})

    assert response.status_code == 200
    assert response.json()["name"] == "GF(3)"
    assert response.json()["parent_id"] == root["id"]


def test_move_to_another_folder(client: TestClient) -> None:
    a = create(client, "A")
    b = create(client, "B")
    child = create(client, "Child", a["id"])

    response = client.patch(f"/folders/{child['id']}", json={"parent_id": b["id"]})

    assert response.status_code == 200
    assert response.json()["parent_id"] == b["id"]
    assert response.json()["name"] == "Child"


def test_null_parent_moves_to_the_root(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])

    response = client.patch(f"/folders/{child['id']}", json={"parent_id": None})

    assert response.status_code == 200
    assert response.json()["parent_id"] is None


def test_rename_to_an_existing_name_is_a_conflict(client: TestClient) -> None:
    create(client, "A")
    b = create(client, "B")

    response = client.patch(f"/folders/{b['id']}", json={"name": "A"})

    assert response.status_code == 409


def test_move_into_itself_is_rejected(client: TestClient) -> None:
    folder = create(client, "Research")

    response = client.patch(f"/folders/{folder['id']}", json={"parent_id": folder["id"]})

    assert response.status_code == 400


def test_move_into_a_descendant_is_rejected(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])
    grandchild = create(client, "n=15", child["id"])

    response = client.patch(f"/folders/{root['id']}", json={"parent_id": grandchild["id"]})

    assert response.status_code == 400
    assert client.get("/folders").status_code == 200  # the tree is still intact


def test_move_under_a_folder_of_another_user_is_not_found(
    client: TestClient, foreign_folder: Folder
) -> None:
    mine = create(client, "Mine")

    response = client.patch(f"/folders/{mine['id']}", json={"parent_id": foreign_folder.id})

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_folder_of_another_user_is_not_found(
    client: TestClient, foreign_folder: Folder, method: str
) -> None:
    url = f"/folders/{foreign_folder.id}"
    if method == "patch":
        response = client.patch(url, json={"name": "Mine now"})
    else:
        response = client.delete(url)

    assert response.status_code == 404


def test_unknown_folder_is_not_found(client: TestClient) -> None:
    assert client.patch("/folders/999999", json={"name": "X"}).status_code == 404
    assert client.delete("/folders/999999").status_code == 404


# --- DELETE /folders/{id} ---


def test_delete_empty_folder(client: TestClient) -> None:
    folder = create(client, "Temp")

    response = client.delete(f"/folders/{folder['id']}")

    assert response.status_code == 204
    assert names(client) == set()


def test_delete_non_empty_folder_needs_confirmation(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])
    create(client, "n=15", child["id"])

    response = client.delete(f"/folders/{root['id']}")

    assert response.status_code == 409
    assert response.json()["detail"]["subfolders"] == 2
    assert names(client) == {"Research", "GF(2)", "n=15"}  # nothing was deleted


def test_force_deletes_the_whole_subtree(client: TestClient) -> None:
    root = create(client, "Research")
    child = create(client, "GF(2)", root["id"])
    create(client, "n=15", child["id"])
    create(client, "Teaching")

    response = client.delete(f"/folders/{root['id']}", params={"force": True})

    assert response.status_code == 204
    assert names(client) == {"Teaching"}
