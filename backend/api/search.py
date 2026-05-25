from fastapi import APIRouter, Query, Depends
import sqlite3

from ..db import get_connection
from ..schemas.common import ok, err
from ..services.drug_service import search_drugs, fuzzy_search

router = APIRouter(prefix="/api/search", tags=["search"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.get("")
def keyword_search(
    q: str = Query(..., min_length=1, description="Drug name query"),
    conn: sqlite3.Connection = Depends(_conn),
):
    """
    GET /api/search?q=met
    实时联想搜索，前缀匹配优先，支持别名。
    """
    results = search_drugs(q, conn)
    if not results:
        return err("NO_RESULTS", f"No drugs found matching '{q}'.",
                   suggestions=["Try the fuzzy search endpoint for spelling variants."])
    return ok(results, source="SQLite", confidence="high")


@router.get("/fuzzy")
def fuzzy_search_endpoint(
    q: str = Query(..., min_length=1),
    conn: sqlite3.Connection = Depends(_conn),
):
    """
    GET /api/search/fuzzy?q=amoxcillin
    拼写容错搜索，auto_redirect=False（不自动跳转）。
    """
    results = fuzzy_search(q, conn)
    return ok(
        {"exact_match": None, "suggestions": results, "auto_redirect": False},
        source="SQLite",
        confidence="medium",
    )


@router.get("/index")
def index_search(
    letter: str = Query(..., min_length=1, max_length=1),
    prefix: str | None = Query(None, min_length=2, max_length=2),
    conn: sqlite3.Connection = Depends(_conn),
):
    """
    GET /api/search/index?letter=M
    GET /api/search/index?letter=M&prefix=ME
    A-Z 分级索引。
    """
    _index_sql = """
        SELECT DISTINCT d.id, d.name, d.generic_name, d.indication_summary, d.risk_level,
            COALESCE(rv.review_count, 0) AS review_count
        FROM search_index si JOIN drugs d ON d.id = si.drug_id
        LEFT JOIN (SELECT drug_id, COUNT(*) AS review_count FROM reviews GROUP BY drug_id) rv
            ON rv.drug_id = d.id
        WHERE {where}
        ORDER BY
            CASE WHEN d.indication_summary IS NOT NULL AND d.indication_summary != '' THEN 0 ELSE 1 END,
            COALESCE(rv.review_count, 0) DESC
        LIMIT 200
    """
    if prefix:
        rows = conn.execute(
            _index_sql.format(where="si.first_two_letters = ?"),
            (prefix.upper(),),
        ).fetchall()
        level = "prefix"
    else:
        rows = conn.execute(
            _index_sql.format(where="si.first_letter = ?"),
            (letter.upper(),),
        ).fetchall()
        level = "letter"

    if not rows:
        return ok(
            {"level": level, "key": prefix or letter, "results": [], "empty": True},
            warnings=[f"No drugs found under '{prefix or letter}'."],
        )

    def _quality(r):
        if r["indication_summary"] and r["review_count"] >= 50:
            return "full"
        if r["indication_summary"]:
            return "partial"
        return "limited"

    results = [
        {
            "drug_id":      r["id"],
            "name":         r["name"],
            "generic_name": r["generic_name"],
            "main_use":     r["indication_summary"],
            "risk_level":   r["risk_level"],
            "review_count": r["review_count"],
            "data_quality": _quality(r),
        }
        for r in rows
    ]
    return ok({"level": level, "key": prefix or letter, "results": results},
              source="SQLite", confidence="high")
