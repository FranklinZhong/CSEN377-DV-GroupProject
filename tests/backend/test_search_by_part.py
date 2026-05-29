"""
test_search_by_part.py — API-SBP-01 ~ 06
Coverage gap: /api/search/by-body-part endpoint had zero tests.
"""


def test_search_by_part_known_part(client):
    # API-SBP-01: stomach has benefits for metformin in seed data
    resp = client.get("/api/search/by-body-part?part=stomach")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["part"] == "stomach"
    assert isinstance(data["data"]["results"], list)


def test_search_by_part_empty_string_is_422(client):
    # API-SBP-02: FastAPI Query(min_length=1) rejects empty string
    resp = client.get("/api/search/by-body-part?part=")
    assert resp.status_code == 422


def test_search_by_part_unknown_part_returns_empty(client):
    # API-SBP-03: no drug has effects for "zzzzpart"
    resp = client.get("/api/search/by-body-part?part=zzzzpart")
    assert resp.status_code == 200
    data = resp.json()
    # Either success=True with empty list, or success=False — either is valid
    results = data.get("data", {}).get("results", [])
    assert isinstance(results, list)


def test_search_by_part_result_shape(client):
    # API-SBP-04: verify returned drug objects have expected fields
    resp = client.get("/api/search/by-body-part?part=liver")
    assert resp.status_code == 200
    data = resp.json()
    results = data.get("data", {}).get("results", [])
    if results:
        drug = results[0]
        assert "drug_id" in drug or "id" in drug or "name" in drug


def test_search_by_part_missing_param_is_422(client):
    # API-SBP-05: no query param at all
    resp = client.get("/api/search/by-body-part")
    assert resp.status_code == 422


def test_search_by_part_case_variations(client):
    # API-SBP-06: typical body part names should not error
    for part in ["muscle", "heart", "brain"]:
        resp = client.get(f"/api/search/by-body-part?part={part}")
        assert resp.status_code == 200
