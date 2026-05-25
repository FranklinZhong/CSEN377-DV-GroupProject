"""
drug_service.py  —  药品查找 / 别名解析 / 搜索索引
"""

import re
import sqlite3
from rapidfuzz import fuzz, process


# ── 规范化（与 build_drug_aliases 保持一致） ─────────────────────────────────

_SUFFIX = re.compile(
    r"\s+(hcl|hbr|hydrochloride|hydrobromide|sodium|potassium|"
    r"sulfate|sulphate|maleate|tartrate|bitartrate|fumarate|"
    r"succinate|acetate|citrate|phosphate|gluconate|besylate|mesylate|"
    r"er|xl|xr|sr|cr|"
    r"solution|suspension|tablet|capsule|patch|"
    r"oral|topical|\d+\s*mg|\d+\s*%)(\s+.*)?$",
    re.IGNORECASE,
)

def normalize(name: str) -> str:
    s = str(name).lower().strip()
    s = re.sub(r"\(.*?\)", "", s)
    s = _SUFFIX.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def find_alt_drug_id(drug_id: int, name: str, conn: sqlite3.Connection) -> int | None:
    """
    When a drug has no effects/reviews, try to find a base-compound drug that does.
    Handles two cases:
    1. Salt variants: "citalopram hbr" → "citalopram" (via expanded normalize)
    2. Combo drugs:  "hydrocodone-acetaminophen" → "hydrocodone" (first component)
    """
    norm = normalize(name)
    original_norm = re.sub(r"\s+", " ", name.lower().strip())

    # Case 1: suffix was stripped, different name → look it up
    if norm != original_norm:
        row = conn.execute(
            "SELECT drug_id FROM search_index WHERE normalized_name = ? AND drug_id != ? LIMIT 1",
            (norm, drug_id),
        ).fetchone()
        if row:
            return row["drug_id"]

    # Case 2: combo drug with hyphen — try first component
    parts = re.split(r"-", name.lower())
    if len(parts) > 1:
        base = parts[0].strip()
        if len(base) >= 4:
            row = conn.execute(
                "SELECT drug_id FROM search_index WHERE normalized_name = ? AND drug_id != ? LIMIT 1",
                (base, drug_id),
            ).fetchone()
            if row:
                return row["drug_id"]

    return None


# ── 搜索 ──────────────────────────────────────────────────────────────────────

_QUALITY_SQL = """
    SELECT DISTINCT
        d.id, d.name, d.generic_name, d.indication_summary, d.risk_level,
        COALESCE(rv.review_count, 0) AS review_count
    FROM search_index si
    JOIN drugs d ON d.id = si.drug_id
    LEFT JOIN (
        SELECT drug_id, COUNT(*) AS review_count FROM reviews GROUP BY drug_id
    ) rv ON rv.drug_id = d.id
    WHERE {where}
    ORDER BY
        CASE WHEN d.indication_summary IS NOT NULL AND d.indication_summary != '' THEN 0 ELSE 1 END,
        COALESCE(rv.review_count, 0) DESC
    LIMIT {limit}
"""


def search_drugs(q: str, conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """
    关键词前缀搜索（支持别名）。
    有官方说明 + 评论多的药优先排列。
    返回 [{ drug_id, name, generic_name, main_use, risk_level, review_count, data_quality, match_type, score }]
    """
    q_norm = normalize(q)

    # 1. 精确前缀匹配
    sql = _QUALITY_SQL.format(where="si.normalized_name LIKE :q", limit=limit)
    rows = conn.execute(sql, {"q": f"{q_norm}%"}).fetchall()
    if rows:
        return [_row_to_result(r, "prefix", 1.0) for r in rows]

    # 2. 通过 drug_aliases 查通用名，再搜索
    alias_row = conn.execute(
        "SELECT canonical_name FROM drug_aliases WHERE alias LIKE ? LIMIT 1",
        (f"{q_norm}%",),
    ).fetchone()
    if alias_row:
        canonical = alias_row["canonical_name"]
        sql = _QUALITY_SQL.format(where="si.normalized_name LIKE :q", limit=limit)
        rows = conn.execute(sql, {"q": f"{normalize(canonical)}%"}).fetchall()
        if rows:
            return [_row_to_result(r, "alias", 0.95) for r in rows]

    return []


def fuzzy_search(q: str, conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """
    模糊搜索（Levenshtein），用于拼写错误场景。
    返回候选列表，auto_redirect=False。
    """
    q_norm = normalize(q)
    all_names = conn.execute(
        "SELECT drug_id, normalized_name FROM search_index"
    ).fetchall()

    candidates = [(r["normalized_name"], r["drug_id"]) for r in all_names]
    matches = process.extract(
        q_norm,
        [c[0] for c in candidates],
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=72,
    )

    results = []
    seen_ids = set()
    for name, score, idx in matches:
        drug_id = candidates[idx][1]
        if drug_id in seen_ids:
            continue
        seen_ids.add(drug_id)

        row = conn.execute(
            "SELECT id, name, generic_name, indication_summary, risk_level FROM drugs WHERE id = ?",
            (drug_id,),
        ).fetchone()
        if row:
            results.append(_row_to_result(row, "fuzzy", round(score / 100, 2)))

    return results


def get_drug_by_id(drug_id: int, conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT * FROM drugs WHERE id = ?", (drug_id,)
    ).fetchone()
    return dict(row) if row else None


def get_drug_by_name(name: str, conn: sqlite3.Connection) -> dict | None:
    """Try exact, then alias resolution, then fuzzy."""
    norm = normalize(name)

    # exact normalized match
    row = conn.execute(
        """
        SELECT d.* FROM drugs d
        JOIN search_index si ON si.drug_id = d.id
        WHERE si.normalized_name = ?
        LIMIT 1
        """,
        (norm,),
    ).fetchone()
    if row:
        return dict(row)

    # alias lookup
    alias = conn.execute(
        "SELECT canonical_name FROM drug_aliases WHERE alias = ? LIMIT 1",
        (norm,),
    ).fetchone()
    if alias:
        return get_drug_by_name(alias["canonical_name"], conn)

    return None


def index_drug(drug_id: int, name: str, conn: sqlite3.Connection):
    """Insert drug into search_index."""
    norm = normalize(name)
    conn.execute(
        """
        INSERT OR IGNORE INTO search_index
            (drug_id, normalized_name, first_letter, first_two_letters)
        VALUES (?, ?, ?, ?)
        """,
        (drug_id, norm,
         norm[0].upper() if norm else "",
         norm[:2].upper() if len(norm) >= 2 else norm.upper()),
    )


# ── 辅助 ──────────────────────────────────────────────────────────────────────

def _data_quality(row) -> str:
    has_indication = bool(row["indication_summary"])
    review_count = row["review_count"] if "review_count" in row.keys() else 0
    if has_indication and review_count >= 50:
        return "full"
    if has_indication:
        return "partial"
    return "limited"


def _row_to_result(row, match_type: str, score: float) -> dict:
    review_count = row["review_count"] if "review_count" in row.keys() else 0
    return {
        "drug_id":      row["id"],
        "name":         row["name"],
        "generic_name": row["generic_name"],
        "main_use":     row["indication_summary"],
        "risk_level":   row["risk_level"],
        "review_count": review_count,
        "data_quality": _data_quality(row),
        "match_type":   match_type,
        "score":        score,
    }
