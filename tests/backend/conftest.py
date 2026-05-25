"""
conftest.py — shared fixtures for all backend tests.

Strategy:
  1. Create a temp SQLite test DB once per session.
  2. Patch backend.db.DB_PATH so every get_connection() call inside the
     FastAPI routers uses the test DB automatically.
  3. Expose `client` (FastAPI TestClient) and `db_conn` (direct connection).
"""

import json
import sqlite3
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


# ── Seed data ─────────────────────────────────────────────────────────────────

GOLDEN = [
    # (id, name, generic, dosage, route, rating, risk, indication, mechanism)
    (1,  "Metformin",    "metformin",    "tablet",    "oral",          4.2, "medium", "type 2 diabetes",       "decreases hepatic glucose production"),
    (2,  "Ibuprofen",    "ibuprofen",    "tablet",    "oral",          4.0, "low",    "pain and fever",        "inhibits COX-1 and COX-2 enzymes"),
    (3,  "Aspirin",      "aspirin",      "tablet",    "oral",          3.8, "low",    "pain, fever, clots",    "inhibits thromboxane synthesis"),
    (4,  "Lisinopril",   "lisinopril",   "tablet",    "oral",          4.1, "low",    "hypertension",          "ACE inhibitor"),
    (5,  "Amoxicillin",  "amoxicillin",  "capsule",   "oral",          4.3, "low",    "bacterial infection",   "penicillin-type antibiotic"),
    (6,  "Sertraline",   "sertraline",   "tablet",    "oral",          3.9, "medium", "depression, OCD",       "selective serotonin reuptake inhibitor"),
    (7,  "Warfarin",     "warfarin",     "tablet",    "oral",          3.5, "high",   "blood clot prevention", "vitamin K antagonist"),
    (8,  "Prednisone",   "prednisone",   "tablet",    "oral",          3.7, "medium", "inflammation",          "corticosteroid"),
    (9,  "Adalimumab",   "adalimumab",   "injection", "subcutaneous",  4.0, "medium", "rheumatoid arthritis",  "TNF-alpha inhibitor"),
    (10, "Gabapentin",   "gabapentin",   "capsule",   "oral",          4.2, "low",    "nerve pain, seizures",  "calcium channel alpha-2-delta ligand"),
]

EXTRA = [
    # (id, name, generic, dosage, route, rating, risk, indication, mechanism)
    (11, "RareDrug",                  "raredrug",                    None,      None,            None,  "unknown", None,            None),
    (12, "Citalopram",                "citalopram",                  "tablet",  "oral",          3.8,   "medium",  "depression",    "SSRI"),
    (13, "Citalopram HBr",            "citalopram hbr",              "tablet",  "oral",          3.8,   "medium",  "depression",    "SSRI"),
    (14, "Hydrocodone",               "hydrocodone",                 "tablet",  "oral",          3.5,   "high",    "pain relief",   "opioid agonist"),
    (15, "Hydrocodone-Acetaminophen", "hydrocodone-acetaminophen",   "tablet",  "oral",          3.5,   "high",    "pain relief",   "opioid + analgesic"),
]


def _seed(conn: sqlite3.Connection) -> None:
    now = datetime.utcnow().isoformat()

    # drugs
    for (did, name, generic, dosage, route, rating, risk, indication, mechanism) in GOLDEN + EXTRA:
        conn.execute(
            """INSERT OR IGNORE INTO drugs
               (id, name, generic_name, indication_summary, mechanism_of_action,
                dosage_form, route, overall_rating, risk_level, data_version, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,'2026Q1',?)""",
            (did, name, generic, indication, mechanism, dosage, route, rating, risk, now),
        )

    # search_index
    index_rows = [
        (1,  "metformin"),
        (2,  "ibuprofen"),
        (3,  "aspirin"),
        (4,  "lisinopril"),
        (5,  "amoxicillin"),
        (6,  "sertraline"),
        (7,  "warfarin"),
        (8,  "prednisone"),
        (9,  "adalimumab"),
        (10, "gabapentin"),
        (11, "raredrug"),
        (12, "citalopram"),
        (13, "citalopram"),               # hbr suffix stripped → same normalized name
        (14, "hydrocodone"),
        (15, "hydrocodone-acetaminophen"),
    ]
    for drug_id, norm in index_rows:
        fl  = norm[0].upper() if norm else ""
        fl2 = norm[:2].upper() if len(norm) >= 2 else norm.upper()
        conn.execute(
            "INSERT OR IGNORE INTO search_index (drug_id, normalized_name, first_letter, first_two_letters) VALUES (?,?,?,?)",
            (drug_id, norm, fl, fl2),
        )

    # drug_aliases
    conn.execute(
        "INSERT OR IGNORE INTO drug_aliases (alias, canonical_name) VALUES ('glucophage','metformin')"
    )

    # effects — metformin: 10 side_effects + 2 benefits
    metformin_se = [
        ("stomach",   "digestive_system",       "Nausea",                    25.0),
        ("stomach",   "digestive_system",       "Diarrhea",                  22.0),
        ("stomach",   "digestive_system",       "Vomiting",                  12.0),
        ("stomach",   "digestive_system",       "Abdominal cramps",          10.0),
        ("liver",     "hepatobiliary_system",   "Lactic acidosis",            2.0),
        ("kidney",    "renal_system",           "Reduced kidney clearance",   3.0),
        ("brain",     "nervous_system",         "Dizziness",                  6.0),
        ("blood",     "hematologic_system",     "Vitamin B12 deficiency",     8.0),
        ("endocrine", "endocrine_system",       "Hypoglycemia risk",          5.0),
        ("skin",      "integumentary_system",   "Skin rash",                  4.0),
    ]
    for bp, svg, name, freq in metformin_se:
        conn.execute(
            """INSERT INTO effects (drug_id, body_part, svg_region, effect_name, effect_type,
               severity, source, frequency, confidence, description) VALUES (1,?,?,?,'side_effect','moderate','FAERS',?,'medium',?)""",
            (bp, svg, name, freq, f"{name} associated with metformin"),
        )

    metformin_be = [
        ("muscle", "musculoskeletal_system", "Reduces insulin resistance", 80.0),
        ("liver",  "hepatobiliary_system",   "Decreases hepatic glucose",  90.0),
    ]
    for bp, svg, name, freq in metformin_be:
        conn.execute(
            """INSERT INTO effects (drug_id, body_part, svg_region, effect_name, effect_type,
               severity, source, frequency, confidence, description) VALUES (1,?,?,?,'benefit','low','FDA',?,'high',?)""",
            (bp, svg, name, freq, f"{name} — benefit of metformin"),
        )

    # effects — ibuprofen: includes stomach / kidney / lung
    ibup_se = [
        ("stomach", "digestive_system",      "GI bleeding",           18.0),
        ("kidney",  "renal_system",          "Acute kidney injury",    7.0),
        ("lung",    "respiratory_system",    "Bronchospasm",           4.0),
        ("heart",   "cardiovascular_system", "Increased CV risk",      5.0),
    ]
    for bp, svg, name, freq in ibup_se:
        conn.execute(
            """INSERT INTO effects (drug_id, body_part, svg_region, effect_name, effect_type,
               severity, source, frequency, confidence) VALUES (2,?,?,?,'side_effect','moderate','FAERS',?,'medium')""",
            (bp, svg, name, freq),
        )

    # effects — hydrocodone: needed for combo drug fallback test
    conn.execute(
        """INSERT INTO effects (drug_id, body_part, svg_region, effect_name, effect_type,
           severity, source, frequency, confidence) VALUES (14,'brain','nervous_system','Drowsiness','side_effect','high','FAERS',45.0,'high')"""
    )

    # reviews — metformin (5 diverse entries)
    reviews = [
        (1, 4.5, "positive", '["stomach"]', "Works great for diabetes control, mild stomach issues at first"),
        (1, 2.0, "negative", '["stomach"]', "Had cramps and diarrhea, could not continue"),
        (1, 3.0, "mixed",    '["stomach"]', "Mild nausea but manageable over time"),
        (1, 5.0, "positive", '["kidney"]',  "No kidney issues after 5 years of use"),
        (1, 1.0, "negative", '["stomach"]', "Severe cramps, stopped after 2 weeks"),
    ]
    for drug_id, rating, sentiment, body_parts, text in reviews:
        conn.execute(
            """INSERT INTO reviews (drug_id, rating, sentiment, review_text, extracted_body_parts, source)
               VALUES (?,?,?,?,?,'WebMD')""",
            (drug_id, rating, sentiment, text, body_parts),
        )

    # review_clusters — metformin
    clusters = [
        (1, "stomach", "positive", 150, '["effective","diabetes"]',    '["Controls blood sugar well"]'),
        (1, "stomach", "negative",  80, '["cramps","nausea"]',         '["Had cramps after first dose"]'),
        (1, "liver",   "mixed",     30, '["liver","enzymes"]',         '["Some liver enzyme changes"]'),
    ]
    for drug_id, bp, sent, cnt, terms, quotes in clusters:
        conn.execute(
            """INSERT INTO review_clusters (drug_id, body_part, sentiment, review_count, top_terms, representative_quotes)
               VALUES (?,?,?,?,?,?)""",
            (drug_id, bp, sent, cnt, terms, quotes),
        )

    # api_cache — pre-seed metformin trend so get_trend_data() hits cache (no external API call)
    quarters = [f"202{y}Q{q}" for y in range(2, 5) for q in range(1, 5)][:9]
    timeline = [
        {
            "quarter": q,
            "body_part": "stomach",
            "svg_region": "digestive_system",
            "report_count": 50 + i * 5,
            "normalized_frequency": round((50 + i * 5) / 90, 4),
            "signal_flag": False,
            "missing": False,
            "confidence": "high",
        }
        for i, q in enumerate(quarters)
    ]
    trend_data = {"timeline": timeline, "signal_events": []}
    now_dt   = datetime.utcnow()
    expires  = now_dt + timedelta(days=7)
    conn.execute(
        """INSERT OR IGNORE INTO api_cache (cache_key, response_json, created_at, expires_at)
           VALUES (?,?,?,?)""",
        ("faers_trend:v1:metformin", json.dumps(trend_data),
         now_dt.isoformat(), expires.isoformat()),
    )

    conn.commit()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    """Create and seed test DB once per session; keep DB_PATH patched throughout."""
    import backend.db as db_mod

    db_path = tmp_path_factory.mktemp("db") / "medinsight_test.db"

    # Patch DB_PATH so init_db() writes the schema into the test DB
    db_mod.DB_PATH = db_path
    db_mod.init_db()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _seed(conn)
    conn.close()

    yield db_path
    # DB_PATH remains patched until session ends (restored by client fixture)


@pytest.fixture(scope="session")
def client(test_db_path):
    """FastAPI TestClient wired to the test DB."""
    import backend.db as db_mod
    from backend.main import app

    orig_path = db_mod.DB_PATH
    db_mod.DB_PATH = test_db_path

    with TestClient(app) as c:
        yield c

    db_mod.DB_PATH = orig_path


@pytest.fixture(scope="session")
def db_conn(test_db_path):
    """Direct SQLite connection for unit tests that call service functions."""
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
