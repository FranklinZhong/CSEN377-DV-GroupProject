"""API integration tests for GET /api/drugs/{id}/overview (v3.5)."""


def test_overview_metformin_has_what_it_treats(client):
    # API-OV-01
    resp = client.get("/api/drugs/1/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["what_it_treats"] is not None


def test_overview_metformin_quick_facts_dosage(client):
    # API-OV-02: metformin has dosage_form='tablet' in seed data
    resp = client.get("/api/drugs/1/overview")
    data = resp.json()
    assert data["data"]["quick_facts"]["dosage_form"] is not None


def test_overview_raredrug_warns_no_data(client):
    # API-OV-03: raredrug has no indication_summary → warnings should mention unavailability
    resp = client.get("/api/drugs/11/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["warnings"]) > 0
    assert any("not available" in w.lower() or "unavailable" in w.lower()
               for w in data["warnings"])


def test_overview_not_found(client):
    resp = client.get("/api/drugs/999999/overview")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "DRUG_NOT_FOUND"
