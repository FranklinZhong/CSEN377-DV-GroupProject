"""API integration tests for /api/search endpoints."""


def test_search_metformin(client):
    # API-SEARCH-01
    resp = client.get("/api/search?q=metformin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert any("metformin" in r["name"].lower() for r in data["data"])


def test_search_empty_query_is_422(client):
    # API-SEARCH-02: FastAPI Query(min_length=1) rejects empty string
    resp = client.get("/api/search?q=")
    assert resp.status_code == 422


def test_search_no_results_error(client):
    # API-SEARCH-03
    resp = client.get("/api/search?q=zzzzqqqxxx")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is False
    assert data["error"]["code"] == "NO_RESULTS"


def test_fuzzy_search_typo(client):
    # API-SEARCH-04: "amoxcillin" → amoxicillin
    resp = client.get("/api/search/fuzzy?q=amoxcillin")
    assert resp.status_code == 200
    data = resp.json()
    sugs = data["data"]["suggestions"]
    assert len(sugs) > 0
    assert any("amoxicillin" in s["name"].lower() for s in sugs)
    assert sugs[0]["score"] >= 0.85


def test_index_search_by_letter(client):
    # API-SEARCH-05
    resp = client.get("/api/search/index?letter=M")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["level"] == "letter"
    assert len(data["data"]["results"]) > 0


def test_index_search_by_prefix(client):
    # API-SEARCH-06
    resp = client.get("/api/search/index?letter=M&prefix=ME")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["level"] == "prefix"
