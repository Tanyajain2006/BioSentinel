from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_success():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "BioSentinel",
        "version": "0.1.0",
    }


def test_unknown_route_returns_404():
    response = client.get("/does-not-exist")

    assert response.status_code == 404
