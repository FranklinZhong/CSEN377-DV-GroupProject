"""API integration tests for GET /api/health."""


def test_health_ok(client):
    # API-HEALTH-01
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"
    assert "drug_count" in data["data"]
    assert data["data"]["drug_count"] > 0
    assert "data_version" in data["data"]
    assert "server_time" in data["data"]
