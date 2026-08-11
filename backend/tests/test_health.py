from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_reports_database_status() -> None:
    app = create_app(database_url="sqlite+pysqlite:///:memory:")

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "database": "ok",
    }

