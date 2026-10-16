import uuid


def test_404_error_contract(client):
    fake_id = uuid.uuid4()
    res = client.get(f"/api/v1/rfqs/{fake_id}")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "RFQ_NOT_FOUND"
    assert "request_id" in data["error"]
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Request-ID"] == data["error"]["request_id"]

def test_422_pydantic_validation_error_contract(client):
    # Invalid limit parameter
    res = client.get("/api/v1/rfqs?limit=999")
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in data["error"]
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0

def test_forced_500_sanitized_contract(client, monkeypatch):
    from app.api import routes

    def fake_health():
        raise RuntimeError("Database connection string postgresql://secret_user:secret_pass@db:5432/db failed with Traceback in /var/app/internal.py")

    monkeypatch.setattr(routes, "check_db_health", fake_health)

    res = client.get("/api/v1/health")
    assert res.status_code == 500
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert "request_id" in data["error"]

    raw_text = res.text
    # PRD Checklist P0 E2: No stack trace, SQL, file path, or secret appears in any error response
    assert "secret_user" not in raw_text
    assert "secret_pass" not in raw_text
    assert "Traceback" not in raw_text
    assert "/var/app" not in raw_text
    assert "postgresql://" not in raw_text
