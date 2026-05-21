from fastapi import APIRouter, Path, Query, HTTPException
import sqlite3

from ..db import db_session
from ..schemas.common import ok, err
from ..services.drug_service import get_drug_by_id, find_alt_drug_id

router = APIRouter(prefix="/api/drugs", tags=["drugs"])


@router.get("/{drug_id}")
def drug_summary(
    drug_id: int = Path(..., gt=0),
):
    with db_session() as conn:
        return _drug_summary(drug_id, conn)


def _drug_summary(drug_id: int, conn: sqlite3.Connection):
    """
    GET /api/drugs/{drug_id}
    Summary bar data: name, FDA status, indication summary, rating, risk level, data version.
    """
    drug = get_drug_by_id(drug_id, conn)
    if not drug:
        raise HTTPException(status_code=404,
            detail=err("DRUG_NOT_FOUND", f"Drug #{drug_id} not found."))

    aliases = conn.execute(
        "SELECT alias FROM drug_aliases WHERE canonical_name = ? LIMIT 10",
        (drug["generic_name"] or drug["name"],),
    ).fetchall()

    coverage = {
        "benefits": conn.execute(
            "SELECT COUNT(*) FROM effects WHERE drug_id = ? AND effect_type = 'benefit'",
            (drug_id,),
        ).fetchone()[0],
        "side_effects": conn.execute(
            "SELECT COUNT(*) FROM effects WHERE drug_id = ? AND effect_type = 'side_effect'",
            (drug_id,),
        ).fetchone()[0],
        "reviews": conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE drug_id = ?",
            (drug_id,),
        ).fetchone()[0],
        "trend_quarters": conn.execute(
            "SELECT COUNT(DISTINCT quarter) FROM faers_quarterly WHERE drug_id = ?",
            (drug_id,),
        ).fetchone()[0],
    }

    return ok(
        {
            "drug_id":      drug["id"],
            "name":         drug["name"],
            "generic_name": drug["generic_name"],
            "brand_name":   drug["brand_name"],
            "manufacturer": drug["manufacturer"],
            "main_use":     drug["indication_summary"],
            "overall_rating": drug["overall_rating"],
            "risk_level":   drug["risk_level"],
            "also_known_as": [r["alias"] for r in aliases],
            "data_sources": ["FDA", "FAERS", "WebMD"],
            "data_version": drug["data_version"],
            "updated_at":   drug["updated_at"],
            "data_coverage": coverage,
        },
        source="SQLite",
        confidence="high",
        data_version=drug["data_version"] or "2026Q1",
    )


@router.get("/{drug_id}/overview")
def drug_overview(
    drug_id: int = Path(..., gt=0),
):
    with db_session() as conn:
        return _drug_overview(drug_id, conn)


def _drug_overview(drug_id: int, conn: sqlite3.Connection):
    """
    GET /api/drugs/{drug_id}/overview  (v3.5)
    Drug Overview card: What it treats / How it works / Quick Facts / Key Indications.
    Data source: OpenFDA Drug Label (indication_summary / mechanism_of_action / dosage_form / route).
    """
    drug = get_drug_by_id(drug_id, conn)
    if not drug:
        raise HTTPException(status_code=404,
            detail=err("DRUG_NOT_FOUND", f"Drug #{drug_id} not found."))

    indication = drug.get("indication_summary")
    mechanism  = drug.get("mechanism_of_action")
    dosage     = drug.get("dosage_form")
    route      = drug.get("route")

    # Extract bullet indications and strip section-header prefixes
    import re as _re

    def _strip_section_prefix(s: str | None) -> str | None:
        if not s:
            return s
        # remove "1 INDICATIONS AND USAGE", "12.1 Mechanism of Action",
        # "3 DOSAGE FORMS AND STRENGTHS" etc.
        return _re.sub(
            r"^\s*(?:\d+(?:\.\d+)?\s+)?"
            r"(?:INDICATIONS?\s+AND\s+USAGE|MECHANISM\s+OF\s+ACTION|"
            r"DOSAGE\s+(?:AND\s+ADMINISTRATION|FORMS?\s+AND\s+STRENGTHS?)|"
            r"CLINICAL\s+PHARMACOLOGY)[\s:.\-]*",
            "", s, flags=_re.IGNORECASE,
        ).strip() or None

    indication = _strip_section_prefix(indication)
    mechanism  = _strip_section_prefix(mechanism)
    dosage     = _strip_section_prefix(dosage)

    key_indications: list[str] = []
    if indication:
        text = indication
        # 1) Bullets
        bullets = _re.findall(r"[●•▪◦*]\s*([^●•▪◦*\n]{6,80})", text)
        # 2) "indicated for X", "treatment of X", "indicated as ... in adults with X"
        if not bullets:
            sent = _re.findall(
                r"(?:indicated\s+(?:for|in|as)|treatment\s+of|"
                r"adults?\s+with|patients?\s+with)\s+"
                r"([^.;,()]{6,80})",
                text, _re.IGNORECASE,
            )
            bullets = sent
        # 3) Hyphen / dash bullets
        if not bullets:
            bullets = _re.findall(r"[\-—]\s+([^\-—\n]{6,80})", text)
        # 4) Semicolon fallback
        if not bullets and ";" in text:
            bullets = [p.strip() for p in text.split(";") if 8 < len(p.strip()) < 80]

        # de-dup & trim
        seen, cleaned = set(), []
        for b in bullets:
            t = b.strip().rstrip(".,;:")
            tl = t.lower()
            if t and tl not in seen and len(t) >= 6:
                seen.add(tl)
                cleaned.append(t)
        key_indications = cleaned[:5]

    warnings = []
    if not indication:
        warnings.append("Indication data not available for this drug.")
    if not mechanism:
        warnings.append("Mechanism of action not available.")

    confidence = "high" if (indication and mechanism) \
        else "medium" if indication \
        else "insufficient"

    return ok(
        {
            "what_it_treats": indication,
            "how_it_works":   mechanism,
            "quick_facts": {
                "dosage_form": dosage,
                "route":       route,
                "rating":      drug.get("overall_rating"),
                "risk_level":  drug.get("risk_level"),
            },
            "key_indications": key_indications,
        },
        source="FDA Drug Label",
        confidence=confidence,
        warnings=warnings,
    )


@router.get("/{drug_id}/benefits")
def drug_benefits(
    drug_id: int = Path(..., gt=0),
):
    with db_session() as conn:
        return _drug_benefits(drug_id, conn)


def _drug_benefits(drug_id: int, conn: sqlite3.Connection):
    """
    GET /api/drugs/{drug_id}/benefits
    Vis 1 Benefits: FDA Drug Label indication → body_part mapping.
    """
    rows = conn.execute(
        """
        SELECT body_part, svg_region, effect_type, effect_name, severity, source, frequency, confidence, description
        FROM effects
        WHERE drug_id = ? AND effect_type = 'benefit'
        ORDER BY frequency DESC
        """,
        (drug_id,),
    ).fetchall()

    if not rows:
        return ok(
            [],
            source="FDA",
            confidence="insufficient",
            warnings=["Official benefit data unavailable for this drug."],
        )

    return ok(
        [dict(r) for r in rows],
        source="FDA Drug Label API",
        confidence="high",
        report_count=len(rows),
    )


@router.get("/{drug_id}/sideeffects")
def drug_side_effects(
    drug_id: int = Path(..., gt=0),
):
    with db_session() as conn:
        return _drug_side_effects(drug_id, conn)


def _drug_side_effects(drug_id: int, conn: sqlite3.Connection):
    """
    GET /api/drugs/{drug_id}/sideeffects
    Vis 1 Side Effects: FAERS adverse event → body_part mapping.
    """
    rows = conn.execute(
        """
        SELECT body_part, svg_region, effect_type, effect_name, severity, source, frequency, confidence, description
        FROM effects
        WHERE drug_id = ? AND effect_type = 'side_effect'
        ORDER BY frequency DESC
        """,
        (drug_id,),
    ).fetchall()

    warnings = []
    confidence = "high"
    used_alt = False

    if not rows:
        # Fallback: try base compound (strip salt suffix or first component of combo)
        drug = get_drug_by_id(drug_id, conn)
        if drug:
            alt_id = find_alt_drug_id(drug_id, drug["name"], conn)
            if alt_id:
                rows = conn.execute(
                    """
                    SELECT body_part, svg_region, effect_type, effect_name, severity, source, frequency, confidence, description
                    FROM effects
                    WHERE drug_id = ? AND effect_type = 'side_effect'
                    ORDER BY frequency DESC
                    """,
                    (alt_id,),
                ).fetchall()
                if rows:
                    used_alt = True

    if not rows:
        warnings.append("No FAERS adverse event data available for this drug.")
        confidence = "insufficient"
    elif used_alt:
        warnings.append("Showing side effects for the base compound (exact data unavailable).")
        confidence = "medium"
    elif len(rows) < 5:
        warnings.append(f"Limited data: only {len(rows)} body regions mapped.")
        confidence = "low"

    return ok(
        [dict(r) for r in rows],
        source="FAERS",
        confidence=confidence,
        report_count=len(rows),
        warnings=warnings,
    )


@router.get("/{drug_id}/reviews/list")
def drug_reviews_list(
    drug_id: int = Path(..., gt=0),
    body_part: str = Query("all", description="Filter by body part or 'all'"),
    sentiment: str = Query("all", description="positive | negative | mixed | neutral | all"),
    rating_min: float = Query(0.0, ge=0.0, le=5.0),
    rating_max: float = Query(5.0, ge=0.0, le=5.0),
    q: str | None = Query(None, max_length=80, description="keyword search"),
    sort: str = Query("recent", description="recent | rating_asc | rating_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    with db_session() as conn:
        return _drug_reviews_list(
            drug_id,
            body_part,
            sentiment,
            rating_min,
            rating_max,
            q,
            sort,
            page,
            page_size,
            conn,
        )


def _drug_reviews_list(
    drug_id: int,
    body_part: str,
    sentiment: str,
    rating_min: float,
    rating_max: float,
    q: str | None,
    sort: str,
    page: int,
    page_size: int,
    conn: sqlite3.Connection,
):
    """
    GET /api/drugs/{drug_id}/reviews/list  (v3.5)
    Paginated patient reviews with body_part filter, sentiment filter, keyword search, and sorting.
    """
    # Build WHERE
    where = ["drug_id = ?"]
    params: list = [drug_id]

    if body_part and body_part != "all":
        where.append("extracted_body_parts LIKE ?")
        params.append(f'%"{body_part}"%')

    if sentiment and sentiment != "all":
        where.append("sentiment = ?")
        params.append(sentiment)

    where.append("(rating IS NULL OR (rating >= ? AND rating <= ?))")
    params.extend([rating_min, rating_max])

    if q:
        where.append("LOWER(review_text) LIKE ?")
        params.append(f"%{q.lower()}%")

    sort_clause = {
        "recent":      "id DESC",
        "rating_desc": "rating DESC NULLS LAST, id DESC",
        "rating_asc":  "rating ASC NULLS LAST, id DESC",
    }.get(sort, "id DESC")

    where_sql = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*) FROM reviews WHERE {where_sql}", params
    ).fetchone()[0]

    offset = (page - 1) * page_size
    rows = conn.execute(
        f"""
        SELECT id, rating, sentiment, review_text, extracted_body_parts, source
        FROM reviews
        WHERE {where_sql}
        ORDER BY {sort_clause}
        LIMIT ? OFFSET ?
        """,
        params + [page_size, offset],
    ).fetchall()

    import json
    reviews = []
    for r in rows:
        try:
            body_parts = json.loads(r["extracted_body_parts"] or "[]")
        except Exception:
            body_parts = []
        reviews.append({
            "id": r["id"],
            "rating": r["rating"],
            "sentiment": r["sentiment"],
            "review_text": r["review_text"],
            "body_parts": body_parts,
            "source": r["source"],
        })

    return ok(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "reviews": reviews,
        },
        source="WebMD",
        confidence="medium",
        report_count=total,
    )


@router.get("/{drug_id}/reviews")
def drug_reviews(
    drug_id: int = Path(..., gt=0),
):
    with db_session() as conn:
        return _drug_reviews(drug_id, conn)


def _drug_reviews(drug_id: int, conn: sqlite3.Connection):
    """
    GET /api/drugs/{drug_id}/reviews
    Vis 3: WebMD reviews clustered by body_part (positive / negative / mixed / neutral).
    """
    import json

    def _fetch_clusters(did: int) -> list:
        rs = conn.execute(
            """
            SELECT body_part, sentiment, review_count, top_terms, representative_quotes
            FROM review_clusters
            WHERE drug_id = ?
            ORDER BY review_count DESC
            """,
            (did,),
        ).fetchall()
        return [
            {
                "body_part":             r["body_part"],
                "sentiment":             r["sentiment"],
                "review_count":          r["review_count"],
                "top_terms":             json.loads(r["top_terms"] or "[]"),
                "representative_quotes": json.loads(r["representative_quotes"] or "[]"),
            }
            for r in rs
        ]

    clusters = _fetch_clusters(drug_id)
    warnings = []
    used_alt = False

    if not clusters:
        drug = get_drug_by_id(drug_id, conn)
        if drug:
            alt_id = find_alt_drug_id(drug_id, drug["name"], conn)
            if alt_id:
                clusters = _fetch_clusters(alt_id)
                if clusters:
                    used_alt = True

    if not clusters:
        warnings.append("No patient review data available for this drug.")
    elif used_alt:
        warnings.append("Showing reviews for the base compound (exact data unavailable).")

    return ok(
        {"clusters": clusters},
        source="WebMD",
        confidence="medium" if clusters else "insufficient",
        report_count=sum(c["review_count"] for c in clusters),
        warnings=warnings,
    )
