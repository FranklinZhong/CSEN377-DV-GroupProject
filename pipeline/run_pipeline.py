"""
MedInsight Pipeline — main entry point

Reads cleaned CSVs and loads them into SQLite medinsight.db.

Steps:
  Step 1  build_drugs        Build drugs table from FAERS + WebMD
  Step 2  load_faers         FAERS signals → effects + faers_quarterly tables
  Step 3  load_webmd         WebMD reviews → reviews + review_clusters tables
  Step 4  build_aliases      drug_aliases table (brand→generic + variants)
  Step 5  build_search_index search_index table
  Step 6  aggregate_rating   reviews.rating → drugs.overall_rating
  Step 7  fill_indication    OpenFDA → drugs.indication_summary / mechanism / dosage / route
  Step 8  build_benefits     indication text → effects (effect_type='benefit')

Usage:
  python pipeline/run_pipeline.py               # all steps
  python pipeline/run_pipeline.py --faers       # FAERS only
  python pipeline/run_pipeline.py --webmd       # WebMD only
  python pipeline/run_pipeline.py --index       # rebuild search index only
  python pipeline/run_pipeline.py --ratings     # aggregate ratings only
  python pipeline/run_pipeline.py --indications # fill indications only
  python pipeline/run_pipeline.py --benefits    # build benefits only
  python pipeline/run_pipeline.py --v35         # run all three fill steps
"""

import re
import sys
import json
import time
import sqlite3
from collections import defaultdict
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Add pipeline directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH
from soc_body_map import BODY_PART_KEYWORDS
from build_drug_aliases import build_aliases, normalize as norm_name

# ── Paths ─────────────────────────────────────────────────────────────────────

_BASE  = Path(__file__).parent.parent
_FAERS = _BASE / "data/processed/FAERS/cleaned_faers_signals_prr_ror.csv"
_WEBMD = _BASE / "data/processed/WebMDReview/cleaned_webmd_reviews.csv"
_DB    = DB_PATH

# ── Constants ─────────────────────────────────────────────────────────────────

_BODY_TO_SVG = {
    "brain": "nervous_system", "eye": "ophthalmologic_system",
    "ear": "auditory_system", "heart": "cardiovascular_system",
    "lung": "respiratory_system", "stomach": "digestive_system",
    "liver": "hepatobiliary_system", "kidney": "renal_system",
    "skin": "integumentary_system", "muscle": "musculoskeletal_system",
    "blood": "hematologic_system", "vascular": "vascular_system",
    "endocrine": "endocrine_system", "immune": "immune_system",
    "reproductive": "reproductive_system",
}

_VADER = SentimentIntensityAnalyzer()

# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def _init_tables(conn: sqlite3.Connection):
    """Create all tables if they don't exist (idempotent; mirrors backend/db.py)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, generic_name TEXT, brand_name TEXT,
            manufacturer TEXT, fda_id TEXT, indication_summary TEXT,
            overall_rating REAL, risk_level TEXT DEFAULT 'unknown',
            data_version TEXT DEFAULT '2026Q1', updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS drug_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL, canonical_name TEXT NOT NULL, confidence REAL DEFAULT 1.0
        );
        CREATE INDEX IF NOT EXISTS idx_alias ON drug_aliases(alias);
        CREATE TABLE IF NOT EXISTS search_index (
            drug_id INTEGER, normalized_name TEXT,
            first_letter TEXT, first_two_letters TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_search_norm  ON search_index(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_search_letter ON search_index(first_letter, first_two_letters);
        CREATE TABLE IF NOT EXISTS effects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL, body_part TEXT NOT NULL, svg_region TEXT NOT NULL,
            effect_name TEXT NOT NULL, effect_type TEXT NOT NULL,
            severity TEXT DEFAULT 'unknown', source TEXT NOT NULL,
            frequency REAL, confidence TEXT DEFAULT 'medium', description TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_effects_drug ON effects(drug_id, effect_type);
        CREATE TABLE IF NOT EXISTS faers_quarterly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL, quarter TEXT NOT NULL,
            body_part TEXT NOT NULL, svg_region TEXT NOT NULL,
            side_effect TEXT NOT NULL, report_count INTEGER DEFAULT 0,
            normalized_frequency REAL, signal_flag INTEGER DEFAULT 0,
            missing INTEGER DEFAULT 0, confidence TEXT DEFAULT 'medium'
        );
        CREATE INDEX IF NOT EXISTS idx_fq_drug ON faers_quarterly(drug_id, quarter);
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL, rating REAL, sentiment TEXT,
            review_text TEXT, extracted_body_parts TEXT,
            extracted_effects TEXT, source TEXT DEFAULT 'WebMD'
        );
        CREATE TABLE IF NOT EXISTS review_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id INTEGER NOT NULL, body_part TEXT NOT NULL,
            sentiment TEXT NOT NULL, review_count INTEGER NOT NULL,
            top_terms TEXT, representative_quotes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_rc_drug ON review_clusters(drug_id);
        CREATE TABLE IF NOT EXISTS api_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL, response_json TEXT NOT NULL,
            created_at TEXT NOT NULL, expires_at TEXT NOT NULL
        );
    """)
    conn.commit()


# ── PT → body_part mapping ────────────────────────────────────────────────────

def _pt_to_body_parts(pt: str) -> list[str]:
    """Map a MedDRA Preferred Term to a list of body_parts via BODY_PART_KEYWORDS."""
    pt_lower = pt.lower()
    found = []
    for body_part, kws in BODY_PART_KEYWORDS.items():
        if any(kw.lower() in pt_lower for kw in kws):
            found.append(body_part)
    return found


def _review_to_body_parts(text: str) -> list[str]:
    """Map review text to body_parts via keyword matching (no spaCy, fast)."""
    t = text.lower()
    found = []
    for body_part, kws in BODY_PART_KEYWORDS.items():
        if any(kw.lower() in t for kw in kws):
            found.append(body_part)
    return found


def _sentiment(text: str) -> str:
    s = _VADER.polarity_scores(str(text))["compound"]
    if s >= 0.05:
        return "positive"
    if s <= -0.05:
        return "negative"
    return "neutral"


def _confidence(count: int) -> str:
    if count >= 50:   return "high"
    if count >= 10:   return "medium"
    if count >= 3:    return "low"
    return "insufficient"


# ── Non-drug filter ───────────────────────────────────────────────────────────

_BAD_DRUG_PATTERNS = [
    re.compile(r'\s+mix$', re.I),
    re.compile(r'pollen', re.I),
    re.compile(r'ragweed', re.I),
    re.compile(r'cat\s+hair', re.I),
    re.compile(r'\b(mugwort|bermuda|juglans|carya|agrostis|dactylis|phleum)\b', re.I),
    re.compile(r'dietary\s+supplement', re.I),
    re.compile(r'hair\s+regrowth', re.I),
    re.compile(r'^acai\b', re.I),
    re.compile(r'^\d+[a-z]+-\d+', re.I),
    re.compile(
        r',\s*(tablet|capsule|solution|suspension|injection|cream|gel|'
        r'patch|ointment|powder|vial|reconstituted|sublingual|'
        r'effervescent|disintegrating|non-aerosol|non-|'
        r'rectal|chewable|medicated|transdermal|extended\s*release|'
        r'drops|irrigation|inhalation|micronized)',
        re.I,
    ),
    re.compile(r'hour\s+(pain|nasal)\s+relief', re.I),
    re.compile(r'^\s*alcohol,\s+rubbing\s*$', re.I),
    re.compile(r',\s*$', re.I),  # trailing comma (truncated / incomplete name)
]

def _is_valid_drug(name: str) -> bool:
    if len(name) < 3:
        return False
    return not any(p.search(name) for p in _BAD_DRUG_PATTERNS)


# ── Step 1: build_drugs ───────────────────────────────────────────────────────

def build_drugs(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Build the drugs table from unique drug names across FAERS and WebMD.
    Returns {canonical_name: drug_id}.
    """
    print("  [1/5] Building drugs table...")
    conn.execute("DELETE FROM drugs")

    names: set[str] = set()

    if _FAERS.exists():
        df = pd.read_csv(_FAERS, usecols=["DRUGNAME_NORM"])
        names.update(df["DRUGNAME_NORM"].str.lower().str.strip().dropna().unique())

    if _WEBMD.exists():
        df = pd.read_csv(_WEBMD, usecols=["Drug"])
        names.update(df["Drug"].str.lower().str.strip().dropna().unique())

    # Normalize, deduplicate, and filter non-drug entries
    canonical_set: set[str] = set()
    for n in names:
        c = norm_name(n)
        if _is_valid_drug(c):
            canonical_set.add(c)
    canonical_set.discard("")

    conn.executemany(
        "INSERT INTO drugs (name, generic_name, brand_name, manufacturer, fda_id, "
        "indication_summary, overall_rating, risk_level, data_version, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(c, c, None, None, None, None, None, "unknown", "2026Q1", None)
         for c in sorted(canonical_set)],
    )
    conn.commit()

    id_map: dict[str, int] = {}
    for row in conn.execute("SELECT id, generic_name FROM drugs"):
        id_map[row["generic_name"]] = row["id"]

    print(f"      → {len(id_map)} drugs inserted.")
    return id_map


def _drug_id(drug_name: str, id_map: dict[str, int]) -> int | None:
    """Map any drug name variant to its drug_id."""
    n = norm_name(drug_name.lower().strip())
    return id_map.get(n)


# ── Step 2: load_faers ────────────────────────────────────────────────────────

def load_faers(conn: sqlite3.Connection, id_map: dict[str, int]):
    if not _FAERS.exists():
        print("  [2/5] FAERS CSV not found — skipping.")
        return

    print("  [2/5] Loading FAERS → effects + faers_quarterly...")
    conn.execute("DELETE FROM effects WHERE source = 'FAERS'")
    conn.execute("DELETE FROM faers_quarterly")

    df = pd.read_csv(
        _FAERS,
        usecols=["DRUGNAME_NORM", "PT_NORM", "QTR", "n_reports",
                 "PRR", "ROR", "any_signal"],
        low_memory=False,
    )
    df["drug_id"] = df["DRUGNAME_NORM"].apply(
        lambda x: _drug_id(x, id_map)
    )
    df = df.dropna(subset=["drug_id"])
    df["drug_id"] = df["drug_id"].astype(int)

    # ── effects (aggregate side effects per drug per body_part)
    effects_agg: dict[tuple, dict] = {}
    for _, row in df.iterrows():
        pts = _pt_to_body_parts(str(row["PT_NORM"]))
        for bp in pts:
            key = (int(row["drug_id"]), bp, str(row["PT_NORM"]))
            if key not in effects_agg:
                effects_agg[key] = {"count": 0, "signal": 0}
            effects_agg[key]["count"] += int(row.get("n_reports", 1))
            if row.get("any_signal"):
                effects_agg[key]["signal"] = 1

    # Keep the highest-count PT per (drug, body_part)
    drug_bp_best: dict[tuple[int, str], dict] = {}
    for (drug_id, bp, pt), val in effects_agg.items():
        k = (drug_id, bp)
        if k not in drug_bp_best or val["count"] > drug_bp_best[k]["count"]:
            drug_bp_best[k] = {"pt": pt, "count": val["count"], "signal": val["signal"]}

    effect_rows = []
    for (drug_id, bp), val in drug_bp_best.items():
        count = val["count"]
        severity = "high" if val["signal"] else ("medium" if count > 10 else "low")
        effect_rows.append((
            drug_id, bp, _BODY_TO_SVG.get(bp, bp),
            val["pt"], "side_effect", severity,
            "FAERS", None, _confidence(count), None,
        ))

    conn.executemany(
        "INSERT INTO effects (drug_id, body_part, svg_region, effect_name, "
        "effect_type, severity, source, frequency, confidence, description) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        effect_rows,
    )

    # ── faers_quarterly
    quarterly_agg: dict[tuple, dict] = {}
    for _, row in df.iterrows():
        pts = _pt_to_body_parts(str(row["PT_NORM"]))
        qtr = str(row.get("QTR", "")).strip()
        if not qtr:
            continue
        for bp in pts:
            key = (int(row["drug_id"]), qtr, bp, str(row["PT_NORM"]))
            if key not in quarterly_agg:
                quarterly_agg[key] = {"count": 0, "signal": 0}
            quarterly_agg[key]["count"] += int(row.get("n_reports", 1))
            if row.get("any_signal"):
                quarterly_agg[key]["signal"] = 1

    fq_rows = []
    for (drug_id, qtr, bp, pt), val in quarterly_agg.items():
        count = val["count"]
        fq_rows.append((
            drug_id, qtr, bp, _BODY_TO_SVG.get(bp, bp),
            pt, count, None, val["signal"], 0, _confidence(count),
        ))

    conn.executemany(
        "INSERT INTO faers_quarterly (drug_id, quarter, body_part, svg_region, "
        "side_effect, report_count, normalized_frequency, signal_flag, missing, confidence) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        fq_rows,
    )

    # normalized_frequency (per drug per quarter, 0-1). Pre-compute maxima so
    # SQLite does not repeatedly scan faers_quarterly for every row.
    conn.execute("DROP TABLE IF EXISTS temp.fq_max")
    conn.execute("""
        CREATE TEMP TABLE fq_max AS
        SELECT drug_id, quarter, MAX(report_count) AS max_count
        FROM faers_quarterly
        GROUP BY drug_id, quarter
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS temp.idx_fq_max ON fq_max(drug_id, quarter)")
    conn.execute("""
        UPDATE faers_quarterly
        SET normalized_frequency = CAST(report_count AS REAL) / (
            SELECT max_count
            FROM fq_max
            WHERE fq_max.drug_id = faers_quarterly.drug_id
              AND fq_max.quarter = faers_quarterly.quarter
        )
    """)

    conn.commit()
    print(f"      → {len(effect_rows)} effect rows, {len(fq_rows)} quarterly rows.")


# ── Step 3: load_webmd ────────────────────────────────────────────────────────

def load_webmd(conn: sqlite3.Connection, id_map: dict[str, int]):
    if not _WEBMD.exists():
        print("  [3/5] WebMD CSV not found — skipping.")
        return

    print("  [3/5] Loading WebMD → reviews + review_clusters...")
    conn.execute("DELETE FROM reviews")
    conn.execute("DELETE FROM review_clusters")

    df = pd.read_csv(
        _WEBMD,
        usecols=["Drug", "Reviews", "Satisfaction", "Condition",
                 "word_count"],
        low_memory=False,
    )
    df["drug_id"] = df["Drug"].apply(lambda x: _drug_id(str(x), id_map))
    df = df.dropna(subset=["drug_id", "Reviews"])
    df["drug_id"] = df["drug_id"].astype(int)
    df["Reviews"] = df["Reviews"].astype(str)

    print(f"      Processing {len(df):,} reviews (VADER + keyword NLP)...")

    # Sentiment analysis
    df["sentiment"] = df["Reviews"].apply(_sentiment)

    # Body part extraction
    df["body_parts"] = df["Reviews"].apply(_review_to_body_parts)

    # Write reviews in batches to avoid memory pressure
    BATCH = 10_000
    total_reviews = 0
    for i in range(0, len(df), BATCH):
        chunk = df.iloc[i : i + BATCH]
        rows = [
            (
                int(r["drug_id"]),
                float(r["Satisfaction"]) if pd.notna(r["Satisfaction"]) else None,
                r["sentiment"],
                r["Reviews"][:500],           # truncate to keep DB size reasonable
                json.dumps(r["body_parts"]),
                None,                          # extracted_effects (reserved for future use)
                "WebMD",
            )
            for _, r in chunk.iterrows()
        ]
        conn.executemany(
            "INSERT INTO reviews (drug_id, rating, sentiment, review_text, "
            "extracted_body_parts, extracted_effects, source) "
            "VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        total_reviews += len(rows)
        if (i // BATCH + 1) % 5 == 0:
            print(f"      {total_reviews:,} reviews written...")
    conn.commit()

    # ── review_clusters (aggregate by drug_id + body_part + sentiment)
    print("      Building review_clusters...")
    df_exploded = df.explode("body_parts")
    df_exploded = df_exploded.dropna(subset=["body_parts"])
    df_exploded = df_exploded[df_exploded["body_parts"] != ""]

    clusters = (
        df_exploded.groupby(["drug_id", "body_parts", "sentiment"])
        .agg(
            review_count=("Reviews", "count"),
            sample_quotes=("Reviews", lambda x: list(x[:2])),
        )
        .reset_index()
    )

    # top_terms: compute once per cluster while scanning exploded reviews.
    cluster_terms: dict[tuple[int, str, str], defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    for drug_id, body_part, sentiment, review in df_exploded[
        ["drug_id", "body_parts", "sentiment", "Reviews"]
    ].itertuples(index=False, name=None):
        kws = BODY_PART_KEYWORDS.get(body_part, [])
        if not kws:
            continue
        text = str(review).lower()
        counts = cluster_terms[(int(drug_id), body_part, sentiment)]
        for kw in kws:
            if kw in text:
                counts[kw] += 1

    cluster_rows = []
    for _, row in clusters.iterrows():
        drug_id   = int(row["drug_id"])
        body_part = row["body_parts"]
        sentiment = row["sentiment"]
        count     = int(row["review_count"])
        quotes    = [q[:200] for q in row["sample_quotes"]]

        term_counts = cluster_terms.get((drug_id, body_part, sentiment), {})
        terms = [k for k, _ in sorted(term_counts.items(), key=lambda x: -x[1])[:5]]

        cluster_rows.append((
            drug_id, body_part, sentiment, count,
            json.dumps(terms), json.dumps(quotes),
        ))

    conn.executemany(
        "INSERT INTO review_clusters (drug_id, body_part, sentiment, review_count, "
        "top_terms, representative_quotes) VALUES (?,?,?,?,?,?)",
        cluster_rows,
    )
    conn.commit()
    print(f"      → {total_reviews:,} reviews, {len(cluster_rows)} cluster rows.")

    # overall_rating per drug
    ratings = df.groupby("drug_id")["Satisfaction"].mean().to_dict()
    for drug_id, rating in ratings.items():
        conn.execute(
            "UPDATE drugs SET overall_rating = ? WHERE id = ?",
            (round(float(rating), 1), int(drug_id)),
        )
    conn.commit()


# ── Step 4: build_search_index ───────────────────────────────────────────────

def build_search_index(conn: sqlite3.Connection):
    print("  [4/5] Building drug_aliases...")
    conn.execute("DELETE FROM drug_aliases")
    alias_rows = build_aliases()
    conn.executemany(
        "INSERT INTO drug_aliases (alias, canonical_name, confidence) VALUES (?,?,?)",
        [(r["alias"], r["canonical_name"], r["confidence"]) for r in alias_rows],
    )
    conn.commit()
    print(f"      → {len(alias_rows)} alias rows.")

    print("  [5/5] Building search_index...")
    conn.execute("DELETE FROM search_index")
    drugs = conn.execute("SELECT id, name, generic_name FROM drugs").fetchall()
    index_rows = []
    for d in drugs:
        name = d["generic_name"] or d["name"]
        n = norm_name(name)
        if n:
            index_rows.append((
                d["id"], n,
                n[0].upper() if n else "",
                n[:2].upper() if len(n) >= 2 else n.upper(),
            ))
    conn.executemany(
        "INSERT INTO search_index (drug_id, normalized_name, first_letter, first_two_letters) "
        "VALUES (?,?,?,?)",
        index_rows,
    )
    conn.commit()
    print(f"      → {len(index_rows)} index entries.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = set(sys.argv[1:])
    full_run  = not args
    v35_only  = args == {"--v35"}

    run_faers       = full_run or "--faers" in args
    run_webmd       = full_run or "--webmd" in args
    run_index       = full_run or "--index" in args
    run_ratings     = full_run or v35_only or "--ratings" in args
    run_indications = full_run or v35_only or "--indications" in args
    run_benefits    = full_run or v35_only or "--benefits" in args

    print("=" * 55)
    print("  MedInsight Pipeline")
    print("=" * 55)

    conn = _conn()
    _init_tables(conn)

    t0 = time.time()

    if not v35_only:
        id_map = build_drugs(conn)          # always needed for steps 1-5
        if run_faers:
            load_faers(conn, id_map)
        if run_webmd:
            load_webmd(conn, id_map)
        if run_index:
            build_search_index(conn)

    # ── v3.5 data fill steps ──────────────────────────────────────────────
    if run_ratings:
        print("  [v3.5] Aggregating ratings...")
        from aggregate_rating import aggregate
        s = aggregate(conn)
        print(f"      → {s['after']:,} drugs now have rating")

    if run_indications:
        print("  [v3.5] Filling indications from OpenFDA (this may take ~20s)...")
        from fill_indication_summary import fill
        s = fill(conn)
        print(f"      → {s['drugs_updated']:,} drugs updated")

    if run_benefits:
        print("  [v3.5] Building benefits...")
        from build_benefits import build
        s = build(conn)
        print(f"      → {s['benefit_rows_inserted']:,} benefit rows for "
              f"{s['drugs_with_benefits']:,} drugs")

    conn.close()

    elapsed = time.time() - t0
    print(f"\n✅ Pipeline done in {elapsed:.1f}s  →  {_DB}")
    final = sqlite3.connect(_DB)
    drug_count = final.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
    rated     = final.execute("SELECT COUNT(*) FROM drugs WHERE overall_rating IS NOT NULL").fetchone()[0]
    indic     = final.execute("SELECT COUNT(*) FROM drugs WHERE indication_summary IS NOT NULL").fetchone()[0]
    benefits  = final.execute("SELECT COUNT(*) FROM effects WHERE effect_type='benefit'").fetchone()[0]
    se        = final.execute("SELECT COUNT(*) FROM effects WHERE effect_type='side_effect'").fetchone()[0]
    print(f"   drugs:        {drug_count:,}")
    print(f"   with rating:  {rated:,}  ({100.0*rated/drug_count:.1f}%)")
    print(f"   with indic.:  {indic:,}  ({100.0*indic/drug_count:.1f}%)")
    print(f"   benefits:     {benefits:,}")
    print(f"   side effects: {se:,}")


if __name__ == "__main__":
    main()
