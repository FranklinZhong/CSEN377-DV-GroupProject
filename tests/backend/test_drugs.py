"""API integration tests for /api/drugs/* endpoints."""


def test_drug_summary_complete_shape(client):
    # API-DRUG-01
    resp = client.get("/api/drugs/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    d = data["data"]
    for field in ("drug_id", "name", "generic_name", "data_coverage"):
        assert field in d, f"missing field: {field}"
    assert d["drug_id"] == 1
    assert d["name"] == "Metformin"


def test_drug_not_found(client):
    # API-DRUG-02: FastAPI wraps HTTPException detail in {"detail": ...}
    resp = client.get("/api/drugs/999999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"]["error"]["code"] == "DRUG_NOT_FOUND"


def test_drug_id_zero_is_422(client):
    # API-DRUG-03: Path(..., gt=0) rejects 0
    resp = client.get("/api/drugs/0")
    assert resp.status_code == 422


def test_drug_benefits_metformin_has_data(client):
    # API-DRUG-04
    resp = client.get("/api/drugs/1/benefits")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) > 0


def test_drug_sideeffects_metformin_at_least_10(client):
    # API-DRUG-05
    resp = client.get("/api/drugs/1/sideeffects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) >= 10


def test_drug_sideeffects_ibuprofen_body_parts(client):
    # API-DRUG-06: ibuprofen should include stomach / kidney / lung
    resp = client.get("/api/drugs/2/sideeffects")
    assert resp.status_code == 200
    body_parts = {e["body_part"] for e in resp.json()["data"]}
    assert "stomach" in body_parts
    assert "kidney"  in body_parts
    assert "lung"    in body_parts


def test_drug_sideeffects_rare_drug_warns(client):
    # API-DRUG-07: raredrug has no effects → warning about missing FAERS data
    resp = client.get("/api/drugs/11/sideeffects")
    assert resp.status_code == 200
    data = resp.json()
    assert any("No FAERS" in w for w in data["warnings"])


def test_drug_sideeffects_combo_fallback_confidence(client):
    # API-DRUG-08: hydrocodone-acetaminophen (id=15) has no direct effects;
    # fallback to hydrocodone (id=14) which HAS effects → confidence=medium
    resp = client.get("/api/drugs/15/sideeffects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["confidence"] == "medium"


def test_drug_reviews_sorted_by_count(client):
    # API-DRUG-09: clusters returned in review_count DESC order
    resp = client.get("/api/drugs/1/reviews")
    assert resp.status_code == 200
    clusters = resp.json()["data"]["clusters"]
    assert len(clusters) > 0
    counts = [c["review_count"] for c in clusters]
    assert counts == sorted(counts, reverse=True)


def test_drug_trend_timeline_length(client):
    # API-DRUG-10: timeline should have ≥ 8 quarters (pre-seeded in api_cache)
    resp = client.get("/api/drugs/1/trend")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["timeline"]) >= 8
