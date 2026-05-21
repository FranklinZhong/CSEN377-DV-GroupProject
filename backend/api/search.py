from fastapi import APIRouter, Query
import sqlite3

from ..db import db_session
from ..schemas.common import ok, err
from ..services.drug_service import search_drugs, fuzzy_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def keyword_search(
    q: str = Query(..., min_length=1, description="Drug name query"),
):
    with db_session() as conn:
        return _keyword_search(q, conn)


def _keyword_search(q: str, conn: sqlite3.Connection):
    """
    GET /api/search?q=met
    Real-time autocomplete: prefix match with alias support.
    """
    results = search_drugs(q, conn)
    if not results:
        return err("NO_RESULTS", f"No drugs found matching '{q}'.",
                   suggestions=["Try the fuzzy search endpoint for spelling variants."])
    return ok(results, source="SQLite", confidence="high")


@router.get("/fuzzy")
def fuzzy_search_endpoint(
    q: str = Query(..., min_length=1),
):
    with db_session() as conn:
        return _fuzzy_search_endpoint(q, conn)


def _fuzzy_search_endpoint(q: str, conn: sqlite3.Connection):
    """
    GET /api/search/fuzzy?q=amoxcillin
    Spelling-error tolerant search; auto_redirect is always False.
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
):
    with db_session() as conn:
        return _index_search(letter, prefix, conn)


def _index_search(
    letter: str,
    prefix: str | None,
    conn: sqlite3.Connection,
):
    """
    GET /api/search/index?letter=M
    GET /api/search/index?letter=M&prefix=ME
    A-Z browse index.
    """
    if prefix:
        rows = conn.execute(
            """
            SELECT DISTINCT d.id, d.name, d.generic_name, d.indication_summary, d.risk_level
            FROM search_index si JOIN drugs d ON d.id = si.drug_id
            WHERE si.first_two_letters = ?
            ORDER BY si.normalized_name
            LIMIT 200
            """,
            (prefix.upper(),),
        ).fetchall()
        level = "prefix"
    else:
        rows = conn.execute(
            """
            SELECT DISTINCT d.id, d.name, d.generic_name, d.indication_summary, d.risk_level
            FROM search_index si JOIN drugs d ON d.id = si.drug_id
            WHERE si.first_letter = ?
            ORDER BY si.normalized_name
            LIMIT 200
            """,
            (letter.upper(),),
        ).fetchall()
        level = "letter"

    if not rows:
        return ok(
            {"level": level, "key": prefix or letter, "results": [], "empty": True},
            warnings=[f"No drugs found under '{prefix or letter}'."],
        )

    results = [
        {
            "drug_id":      r["id"],
            "name":         r["name"],
            "generic_name": r["generic_name"],
            "main_use":     r["indication_summary"],
            "risk_level":   r["risk_level"],
        }
        for r in rows
    ]
    return ok({"level": level, "key": prefix or letter, "results": results},
              source="SQLite", confidence="high")
