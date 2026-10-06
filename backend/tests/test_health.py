from fastapi.testclient import TestClient

from deltaweb.main import app


def test_healthz_does_not_need_the_database() -> None:
    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_checks_the_database(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
