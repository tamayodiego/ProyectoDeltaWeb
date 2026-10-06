"""POST /delta-matroids/generate. No database needed: it only computes.

The app's lifespan starts a real pool of worker processes, so these tests also check
that the work really runs (and its errors come back) across processes.
"""

from collections.abc import Iterator

import numpy as np
import pytest
from fastapi.testclient import TestClient

from deltaweb.domain.deltamatroid import DeltaMatroid
from deltaweb.main import app


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    with TestClient(app) as client:  # "with" runs the lifespan: starts the worker pool
        yield client


def generate(api: TestClient, **body: object) -> dict:
    response = api.post("/delta-matroids/generate", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_symmetric_matrix_over_gf2(api: TestClient) -> None:
    # Singletons det 0, pairs det -1, whole matrix det 2 (even): only the pairs are feasible
    result = generate(api, matrix=[[0, 1, 1], [1, 0, 1], [1, 1, 0]], field=2)

    assert result["ground_set"] == ["1", "2", "3"]
    assert result["feasible"] == [0b000, 0b011, 0b101, 0b110]
    assert result["fingerprint"] == [1, 0, 3, 0]
    assert result["frequencies"] == [2, 2, 2]
    assert result["field"] == 2


def test_skew_symmetric_matrix_over_gf3(api: TestClient) -> None:
    result = generate(api, matrix=[[0, 1], [-1, 0]], field=3)

    assert result["feasible"] == [0b00, 0b11]
    assert result["fingerprint"] == [1, 0, 1]


def test_custom_labels(api: TestClient) -> None:
    result = generate(api, matrix=[[0, 1], [-1, 0]], field=3, labels=["a", " b "])

    assert result["ground_set"] == ["a", "b"]


def test_same_result_as_the_domain_class(api: TestClient) -> None:
    rng = np.random.default_rng(7)
    upper = np.triu(rng.integers(0, 2, size=(8, 8)))
    matrix = upper + np.triu(upper, 1).T
    expected = DeltaMatroid("D", field=2, matrix=matrix.astype(np.int64))

    result = generate(api, matrix=matrix.tolist(), field=2)

    assert result["feasible"] == [int(mask) for mask in expected.feasible_family]
    assert result["fingerprint"] == list(expected.fingerprint)
    assert result["frequencies"] == expected.frequencies


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"matrix": [[0, 1], [-1, 0]], "field": 2}, "GF(2) requires a symmetric matrix"),
        ({"matrix": [[1, 0], [0, 1]], "field": 3}, "GF(3) requires a skew-symmetric matrix"),
        ({"matrix": [[2, 0], [0, 1]], "field": 2}, "neither symmetric"),
        ({"matrix": [[0, 1], [0, 0]], "field": 2}, "neither symmetric"),
        ({"matrix": [[0, 1, 0], [1, 0]], "field": 2}, "square"),
        ({"matrix": [], "field": 2}, "at least 1"),
        ({"matrix": [[0]], "field": 5}, "field"),
        ({"matrix": [[0] * 16] * 16, "field": 2}, "exceeds the limit of 15"),
        ({"matrix": [[0, 1], [1, 0]], "field": 2, "labels": ["a"]}, "expected 2 labels"),
        ({"matrix": [[0, 1], [1, 0]], "field": 2, "labels": ["a", "a"]}, "unique"),
    ],
)
def test_invalid_requests_are_rejected(api: TestClient, body: dict, reason: str) -> None:
    response = api.post("/delta-matroids/generate", json=body)

    assert response.status_code == 422
    assert reason in response.text
