"""API integration tests for GET /api/drugs/{id}/reviews/list (v3.5)."""


def test_reviews_list_body_part_filter(client):
    # API-RL-01: filter by stomach → at least 1 result
    resp = client.get("/api/drugs/1/reviews/list?body_part=stomach&page=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert len(data["reviews"]) <= 10


def test_reviews_list_sentiment_filter(client):
    # API-RL-02: sentiment=negative → all returned rows are negative
    resp = client.get("/api/drugs/1/reviews/list?sentiment=negative")
    assert resp.status_code == 200
    reviews = resp.json()["data"]["reviews"]
    assert len(reviews) > 0
    for review in reviews:
        assert review["sentiment"] == "negative"


def test_reviews_list_rating_min_filter(client):
    # API-RL-03: rating_min=4 → all ratings ≥ 4
    resp = client.get("/api/drugs/1/reviews/list?rating_min=4")
    assert resp.status_code == 200
    reviews = resp.json()["data"]["reviews"]
    assert len(reviews) > 0
    for review in reviews:
        if review["rating"] is not None:
            assert review["rating"] >= 4


def test_reviews_list_keyword_search(client):
    # API-RL-04: q=cramps → all review_text contains "cramps"
    resp = client.get("/api/drugs/1/reviews/list?q=cramps")
    assert resp.status_code == 200
    reviews = resp.json()["data"]["reviews"]
    assert len(reviews) > 0
    for r in reviews:
        assert "cramps" in r["review_text"].lower()


def test_reviews_list_sort_rating_desc(client):
    # API-RL-05: sort=rating_desc → ratings in descending order
    resp = client.get("/api/drugs/1/reviews/list?sort=rating_desc&page_size=10")
    assert resp.status_code == 200
    ratings = [r["rating"] for r in resp.json()["data"]["reviews"]
               if r["rating"] is not None]
    if len(ratings) > 1:
        assert ratings == sorted(ratings, reverse=True)


def test_reviews_list_page_overflow_empty(client):
    # API-RL-06: page far beyond range → empty list but total > 0
    resp = client.get("/api/drugs/1/reviews/list?page=999")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["reviews"] == []
    assert data["total"] > 0
