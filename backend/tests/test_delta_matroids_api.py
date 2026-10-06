"""Tests for saved delta-matroids (Phase 2a, last task). Needs Docker (see conftest.py).

Expected API, in ``src/deltaweb/api/delta_matroids.py`` (same router as /generate), with
schemas in ``src/deltaweb/schemas/delta_matroid.py`` and a ``DeltaMatroidRecord`` model
(table ``delta_matroids``; the name ``DeltaMatroid`` is taken by the domain class):

    POST   /delta-matroids        {"name", "folder_id"?, "matrix", "field", "labels"?}  -> 201 full
    GET    /delta-matroids                                        -> 200 list of summaries
    GET    /delta-matroids/{id}                                   -> 200 full
    PATCH  /delta-matroids/{id}   {"name"?, "folder_id"?}         -> 200 full
    DELETE /delta-matroids/{id}                                   -> 204

full    = {"id", "name", "folder_id", "field", "matrix", "ground_set", "feasible",
           "fingerprint", "frequencies", "created_at"}
summary = {"id", "name", "folder_id", "field", "size", "feasible_count", "created_at"}

Rules (decided with the user):
- The server generates from the matrix (reusing the worker pool), then saves.
- "folder_id": null = the root. A folder of another user -> 404.
- Unique names in the same place (case-sensitive) -> 409, like folders.
- Only the family is stored; fingerprint and frequencies are recalculated when read.
- Someone else's delta-matroid -> 404. Same name/matrix rules as /generate -> 422.
- Deleting a folder: the 409 also reports ``detail["delta_matroids"]`` (every level),
  and force=true deletes them too.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from deltaweb.models import Folder, User

GF2_MATRIX = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]  # feasible: {}, {1,2}, {1,3}, {2,3}
GF3_MATRIX = [[0, 1], [-1, 0]]  # feasible: {}, {1,2}


def save(client: TestClient, name: str, folder_id: int | None = None, **extra: object) -> dict:
    body = {"name": name, "folder_id": folder_id, "matrix": GF2_MATRIX, "field": 2, **extra}
    response = client.post("/delta-matroids", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def folder(client: TestClient, name: str, parent_id: int | None = None) -> int:
    response = client.post("/folders", json={"name": name, "parent_id": parent_id})
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


@pytest.fixture
def foreign(session: Session) -> Folder:
    """A folder of another user."""
    other = User(email="other@deltaweb.local")
    session.add(other)
    session.flush()
    f = Folder(name="Not yours", owner_id=other.id)
    session.add(f)
    session.flush()
    return f


# --- POST ---


def test_save_generates_and_returns_everything(client: TestClient) -> None:
    dm = save(client, "Triangle", folder(client, "Research"))

    assert dm["name"] == "Triangle"
    assert dm["field"] == 2
    assert dm["matrix"] == GF2_MATRIX
    assert dm["ground_set"] == ["1", "2", "3"]
    assert dm["feasible"] == [0b000, 0b011, 0b101, 0b110]
    assert dm["fingerprint"] == [1, 0, 3, 0]
    assert dm["frequencies"] == [2, 2, 2]
    assert isinstance(dm["id"], int)
    assert "created_at" in dm


def test_save_in_the_root(client: TestClient) -> None:
    assert save(client, "Loose")["folder_id"] is None


def test_save_with_labels_over_gf3(client: TestClient) -> None:
    dm = save(client, "Pair", matrix=GF3_MATRIX, field=3, labels=["a", "b"])

    assert dm["ground_set"] == ["a", "b"]
    assert dm["feasible"] == [0b00, 0b11]


def test_invalid_matrix_is_not_saved(client: TestClient) -> None:
    body = {"name": "Bad", "matrix": GF3_MATRIX, "field": 2}  # skew-symmetric over GF(2)

    assert client.post("/delta-matroids", json=body).status_code == 422
    assert client.get("/delta-matroids").json() == []


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_rejected(client: TestClient, name: str) -> None:
    body = {"name": name, "matrix": GF2_MATRIX, "field": 2}

    assert client.post("/delta-matroids", json=body).status_code == 422


def test_duplicate_name_in_the_same_place_is_a_conflict(client: TestClient) -> None:
    research = folder(client, "Research")
    save(client, "Triangle", research)

    body = {"name": "Triangle", "folder_id": research, "matrix": GF2_MATRIX, "field": 2}
    assert client.post("/delta-matroids", json=body).status_code == 409


def test_duplicate_name_in_the_root_is_a_conflict(client: TestClient) -> None:
    save(client, "Triangle")

    body = {"name": "Triangle", "matrix": GF2_MATRIX, "field": 2}
    assert client.post("/delta-matroids", json=body).status_code == 409


def test_same_name_in_different_folders_is_allowed(client: TestClient) -> None:
    save(client, "Triangle", folder(client, "A"))
    save(client, "Triangle", folder(client, "B"))
    save(client, "triangle", None)  # case-sensitive


def test_folder_of_another_user_is_not_found(client: TestClient, foreign: Folder) -> None:
    body = {"name": "Sneaky", "folder_id": foreign.id, "matrix": GF2_MATRIX, "field": 2}

    assert client.post("/delta-matroids", json=body).status_code == 404


# --- GET ---


def test_list_returns_light_summaries(client: TestClient) -> None:
    research = folder(client, "Research")
    save(client, "Triangle", research)
    save(client, "Pair", matrix=GF3_MATRIX, field=3)

    summaries = {s["name"]: s for s in client.get("/delta-matroids").json()}

    assert set(summaries) == {"Triangle", "Pair"}
    assert summaries["Triangle"]["folder_id"] == research
    assert summaries["Triangle"]["size"] == 3
    assert summaries["Triangle"]["feasible_count"] == 4
    assert summaries["Pair"]["field"] == 3
    assert "feasible" not in summaries["Triangle"]  # the family can be big: not in the list


def test_get_one_recalculates_fingerprint_and_frequencies(client: TestClient) -> None:
    saved = save(client, "Triangle")

    response = client.get(f"/delta-matroids/{saved['id']}")

    assert response.status_code == 200
    assert response.json() == saved


def test_delta_matroid_of_another_user_is_not_found(
    client: TestClient, session: Session, foreign: Folder
) -> None:
    from deltaweb.models import DeltaMatroidRecord  # imported here: the model is yours to add

    record = DeltaMatroidRecord(
        name="Theirs",
        owner_id=foreign.owner_id,
        folder_id=foreign.id,
        field=2,
        matrix=[[0]],
        ground_set=["1"],
        feasible=[0],
    )
    session.add(record)
    session.flush()

    assert client.get(f"/delta-matroids/{record.id}").status_code == 404
    assert client.patch(f"/delta-matroids/{record.id}", json={"name": "Mine"}).status_code == 404
    assert client.delete(f"/delta-matroids/{record.id}").status_code == 404
    assert client.get("/delta-matroids").json() == []


def test_unknown_delta_matroid_is_not_found(client: TestClient) -> None:
    assert client.get("/delta-matroids/999999").status_code == 404


# --- PATCH ---


def test_rename(client: TestClient) -> None:
    dm = save(client, "Triangle")

    response = client.patch(f"/delta-matroids/{dm['id']}", json={"name": "K3"})

    assert response.status_code == 200
    assert response.json()["name"] == "K3"
    assert response.json()["feasible"] == dm["feasible"]


def test_move_to_a_folder_and_back_to_the_root(client: TestClient) -> None:
    dm = save(client, "Triangle")
    research = folder(client, "Research")

    moved = client.patch(f"/delta-matroids/{dm['id']}", json={"folder_id": research}).json()
    assert moved["folder_id"] == research
    assert moved["name"] == "Triangle"

    back = client.patch(f"/delta-matroids/{dm['id']}", json={"folder_id": None}).json()
    assert back["folder_id"] is None


def test_move_onto_an_existing_name_is_a_conflict(client: TestClient) -> None:
    research = folder(client, "Research")
    save(client, "Triangle", research)
    loose = save(client, "Triangle")

    response = client.patch(f"/delta-matroids/{loose['id']}", json={"folder_id": research})

    assert response.status_code == 409


def test_move_to_a_folder_of_another_user_is_not_found(client: TestClient, foreign: Folder) -> None:
    dm = save(client, "Triangle")

    response = client.patch(f"/delta-matroids/{dm['id']}", json={"folder_id": foreign.id})

    assert response.status_code == 404


# --- DELETE ---


def test_delete(client: TestClient) -> None:
    dm = save(client, "Triangle")

    assert client.delete(f"/delta-matroids/{dm['id']}").status_code == 204
    assert client.get(f"/delta-matroids/{dm['id']}").status_code == 404


# --- Deleting folders now also counts delta-matroids ---


def test_deleting_a_folder_reports_its_delta_matroids(client: TestClient) -> None:
    research = folder(client, "Research")
    child = folder(client, "GF(2)", research)
    save(client, "A", research)
    save(client, "B", child)

    response = client.delete(f"/folders/{research}")

    assert response.status_code == 409
    assert response.json()["detail"]["subfolders"] == 1
    assert response.json()["detail"]["delta_matroids"] == 2
    assert len(client.get("/delta-matroids").json()) == 2  # nothing was deleted


def test_folder_with_only_delta_matroids_also_needs_confirmation(client: TestClient) -> None:
    research = folder(client, "Research")
    save(client, "A", research)

    response = client.delete(f"/folders/{research}")

    assert response.status_code == 409
    assert response.json()["detail"]["subfolders"] == 0
    assert response.json()["detail"]["delta_matroids"] == 1


def test_force_deletes_the_delta_matroids_too(client: TestClient) -> None:
    research = folder(client, "Research")
    save(client, "A", folder(client, "GF(2)", research))
    save(client, "Keep")

    response = client.delete(f"/folders/{research}", params={"force": True})

    assert response.status_code == 204
    assert [s["name"] for s in client.get("/delta-matroids").json()] == ["Keep"]
