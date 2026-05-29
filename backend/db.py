"""
SQLite database connection and initialization.

Tables are created here if they don't exist yet so the backend can start
even before the pipeline has been run (it will just return empty results).
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "processed" / "medinsight.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_DEFAULT_DB)))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # allow concurrent reads
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup.
    Also ALTERs in any v3.5 columns missing on legacy databases."""
    with db_session() as conn:
        # Idempotent ALTERs for v3.5 columns on legacy DBs
        existing = {r[1] for r in conn.execute("PRAGMA table_info(drugs)")}
        for col, ctype in [
            ("mechanism_of_action", "TEXT"),
            ("dosage_form",         "TEXT"),
            ("route",               "TEXT"),
        ]:
            if col not in existing and existing:
                conn.execute(f"ALTER TABLE drugs ADD COLUMN {col} {ctype}")

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS drugs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL,
                generic_name        TEXT,
                brand_name          TEXT,
                manufacturer        TEXT,
                fda_id              TEXT,
                indication_summary  TEXT,
                mechanism_of_action TEXT,
                dosage_form         TEXT,
                route               TEXT,
                overall_rating      REAL,
                risk_level          TEXT DEFAULT 'unknown',
                data_version        TEXT DEFAULT '2026Q1',
                updated_at          TEXT
            );

            CREATE TABLE IF NOT EXISTS drug_aliases (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                alias           TEXT NOT NULL,
                canonical_name  TEXT NOT NULL,
                confidence      REAL DEFAULT 1.0
            );
            CREATE INDEX IF NOT EXISTS idx_alias ON drug_aliases(alias);

            CREATE TABLE IF NOT EXISTS search_index (
                drug_id             INTEGER,
                normalized_name     TEXT,
                first_letter        TEXT,
                first_two_letters   TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_search_norm
                ON search_index(normalized_name);
            CREATE INDEX IF NOT EXISTS idx_search_letter
                ON search_index(first_letter, first_two_letters);

            CREATE TABLE IF NOT EXISTS effects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id     INTEGER NOT NULL,
                body_part   TEXT NOT NULL,
                svg_region  TEXT NOT NULL,
                effect_name TEXT NOT NULL,
                effect_type TEXT NOT NULL,
                severity    TEXT DEFAULT 'unknown',
                source      TEXT NOT NULL,
                frequency   REAL,
                confidence  TEXT DEFAULT 'medium',
                description TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_effects_drug
                ON effects(drug_id, effect_type);

            CREATE TABLE IF NOT EXISTS faers_quarterly (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id              INTEGER NOT NULL,
                quarter              TEXT NOT NULL,
                body_part            TEXT NOT NULL,
                svg_region           TEXT NOT NULL,
                side_effect          TEXT NOT NULL,
                report_count         INTEGER DEFAULT 0,
                normalized_frequency REAL,
                signal_flag          INTEGER DEFAULT 0,
                missing              INTEGER DEFAULT 0,
                confidence           TEXT DEFAULT 'medium'
            );
            CREATE INDEX IF NOT EXISTS idx_fq_drug
                ON faers_quarterly(drug_id, quarter);

            CREATE TABLE IF NOT EXISTS reviews (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id              INTEGER NOT NULL,
                rating               REAL,
                sentiment            TEXT,
                review_text          TEXT,
                extracted_body_parts TEXT,
                extracted_effects    TEXT,
                source               TEXT DEFAULT 'WebMD'
            );

            CREATE TABLE IF NOT EXISTS review_clusters (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id              INTEGER NOT NULL,
                body_part            TEXT NOT NULL,
                sentiment            TEXT NOT NULL,
                review_count         INTEGER NOT NULL,
                top_terms            TEXT,
                representative_quotes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_rc_drug
                ON review_clusters(drug_id);

            CREATE TABLE IF NOT EXISTS api_cache (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key     TEXT UNIQUE NOT NULL,
                response_json TEXT NOT NULL,
                created_at    TEXT NOT NULL,
                expires_at    TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cache_key
                ON api_cache(cache_key);
        """)
