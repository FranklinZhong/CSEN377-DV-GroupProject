"""
fill_indication_summary.py — Extract indication / mechanism / dosage from OpenFDA Drug Label

Streams the OpenFDA clean_label_master.csv (~5.7 GB) in chunks, matches rows to
drug_id via openfda_generic_name, then writes the following cleaned fields back to
the drugs table (columns are added automatically on first run via idempotent ALTER):

  drugs.indication_summary    (pre-existing)
  drugs.mechanism_of_action   (new)
  drugs.dosage_form           (new)
  drugs.route                 (new)

Usage:
    python pipeline/fill_indication_summary.py
    python pipeline/fill_indication_summary.py --limit 200000   # scan only first N rows (debug)
"""

import re
import sys
import sqlite3
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build_drug_aliases import normalize as norm_name  # noqa: E402

_BASE = Path(__file__).parent.parent
_DB = _BASE / "data" / "processed" / "medinsight.db"
_CSV = _BASE / "data" / "processed" / "OpenFDA" / "data" / "processed" / "clean_label_master.csv"

_CHUNK = 20_000  # rows per pandas chunk
_MAX_INDIC = 350
_MAX_MECH = 250
_MAX_DOSE = 200

# ── Text cleaning helpers ─────────────────────────────────────────────────────

_LEAD_NOISE = re.compile(
    r"^\s*(\d+\s*)?(INDICATIONS?\s+AND\s+USAGE|MECHANISM\s+OF\s+ACTION|"
    r"DOSAGE\s+AND\s+ADMINISTRATION|CLINICAL\s+PHARMACOLOGY)[\s:.\-]*",
    re.IGNORECASE,
)
_TAIL_REF = re.compile(r"\s*\(\s*\d+(\.\d+)*\s*\)\s*$")  # "( 1 )" "(2.1)"
_WHITESPACE = re.compile(r"\s+")


def _clean_text(raw, max_len: int) -> str | None:
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    s = _LEAD_NOISE.sub("", s)
    s = _WHITESPACE.sub(" ", s).strip()
    if not s:
        return None

    # Cut at sentence boundary near max_len
    if len(s) > max_len:
        cut = s[:max_len]
        last_period = max(cut.rfind(". "), cut.rfind("."))
        if last_period > max_len * 0.6:
            s = cut[: last_period + 1].strip()
        else:
            s = cut.strip() + "…"

    s = _TAIL_REF.sub("", s).strip()
    return s or None


def _normalize_for_match(name: str) -> list[str]:
    """OpenFDA generic name may be combo (A AND B). Return all candidate norms."""
    if not isinstance(name, str):
        return []
    base = norm_name(name)
    cands = {base}
    # Split combo drugs
    for sep in [" and ", "-", "+", "/"]:
        if sep in base:
            for part in base.split(sep):
                p = part.strip()
                if len(p) >= 4:
                    cands.add(p)
    return [c for c in cands if c]


# ── Schema extension (idempotent) ────────────────────────────────────────────

def _ensure_columns(conn: sqlite3.Connection):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(drugs)")}
    additions = {
        "mechanism_of_action": "TEXT",
        "dosage_form":         "TEXT",
        "route":               "TEXT",
    }
    for col, ctype in additions.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE drugs ADD COLUMN {col} {ctype}")
            print(f"      [schema] added column drugs.{col}")
    conn.commit()


# ── Main logic ────────────────────────────────────────────────────────────────

def fill(conn: sqlite3.Connection, row_limit: int | None = None) -> dict:
    _ensure_columns(conn)

    print("  Loading drug name → id map...")
    id_map: dict[str, int] = {}
    for row in conn.execute("SELECT id, name, generic_name FROM drugs"):
        for n in [row["name"], row["generic_name"]]:
            if n:
                id_map[norm_name(n)] = row["id"]
    print(f"      → {len(id_map):,} canonical names indexed")

    # Collect {drug_id: {indication, mechanism, dosage, route}}, keeping the first non-null value
    collected: dict[int, dict[str, str | None]] = {}

    usecols = [
        "openfda_generic_name", "openfda_brand_name", "openfda_route",
        "indications_and_usage", "mechanism_of_action",
        "dosage_forms_and_strengths", "dosage_and_administration",
    ]

    t0 = time.time()
    total_rows = 0
    matched_rows = 0
    chunks_done = 0
    print(f"  Streaming {_CSV.name} (chunks of {_CHUNK:,}) ...")

    for chunk in pd.read_csv(_CSV, usecols=usecols, chunksize=_CHUNK, low_memory=False):
        for _, r in chunk.iterrows():
            total_rows += 1
            if row_limit and total_rows > row_limit:
                break

            # Try both generic_name and brand_name as match candidates
            candidates: list[str] = []
            candidates.extend(_normalize_for_match(r.get("openfda_generic_name")))
            candidates.extend(_normalize_for_match(r.get("openfda_brand_name")))

            for cand in candidates:
                drug_id = id_map.get(cand)
                if not drug_id:
                    continue

                bucket = collected.setdefault(
                    drug_id, {"indication": None, "mechanism": None,
                              "dosage": None, "route": None}
                )

                if not bucket["indication"]:
                    txt = _clean_text(r.get("indications_and_usage"), _MAX_INDIC)
                    if txt:
                        bucket["indication"] = txt
                if not bucket["mechanism"]:
                    txt = _clean_text(r.get("mechanism_of_action"), _MAX_MECH)
                    if txt:
                        bucket["mechanism"] = txt
                if not bucket["dosage"]:
                    txt = _clean_text(r.get("dosage_forms_and_strengths"), _MAX_DOSE)
                    if not txt:
                        txt = _clean_text(r.get("dosage_and_administration"), _MAX_DOSE)
                    if txt:
                        bucket["dosage"] = txt
                if not bucket["route"]:
                    rt = r.get("openfda_route")
                    if isinstance(rt, str) and rt.strip():
                        bucket["route"] = rt.strip().lower().split(",")[0]

                matched_rows += 1
                break  # one drug_id per CSV row is enough

        chunks_done += 1
        if chunks_done % 5 == 0:
            elapsed = time.time() - t0
            print(f"      {total_rows:,} rows | {matched_rows:,} matches | "
                  f"{len(collected):,} drugs covered | {elapsed:.0f}s")

        if row_limit and total_rows > row_limit:
            break

    print(f"  → Done streaming: {total_rows:,} rows scanned, "
          f"{matched_rows:,} matched, {len(collected):,} drugs collected "
          f"({time.time() - t0:.0f}s)")

    print("  Writing back to drugs table ...")
    upd_rows = [
        (b["indication"], b["mechanism"], b["dosage"], b["route"], drug_id)
        for drug_id, b in collected.items()
    ]
    conn.executemany(
        "UPDATE drugs SET indication_summary = COALESCE(?, indication_summary), "
        "mechanism_of_action = COALESCE(?, mechanism_of_action), "
        "dosage_form = COALESCE(?, dosage_form), "
        "route = COALESCE(?, route) WHERE id = ?",
        upd_rows,
    )
    conn.commit()

    stats = {
        "rows_scanned":   total_rows,
        "rows_matched":   matched_rows,
        "drugs_updated":  len(collected),
    }
    for col in ["indication_summary", "mechanism_of_action", "dosage_form", "route"]:
        cnt = conn.execute(
            f"SELECT COUNT(*) FROM drugs WHERE {col} IS NOT NULL"
        ).fetchone()[0]
        stats[col] = cnt
    return stats


def main():
    row_limit = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        row_limit = int(sys.argv[i + 1])

    if not _CSV.exists():
        print(f"❌ OpenFDA CSV not found: {_CSV}")
        sys.exit(1)

    print("=" * 55)
    print("  Fill Indication / Mechanism / Dosage from OpenFDA")
    print("=" * 55)

    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    try:
        stats = fill(conn, row_limit=row_limit)
    finally:
        conn.close()

    total = sqlite3.connect(_DB).execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
    print(f"\n  rows scanned    : {stats['rows_scanned']:,}")
    print(f"  rows matched    : {stats['rows_matched']:,}")
    print(f"  drugs touched   : {stats['drugs_updated']:,}")
    print(f"\n  Coverage (out of {total:,} drugs):")
    for col in ["indication_summary", "mechanism_of_action", "dosage_form", "route"]:
        cnt = stats[col]
        print(f"    {col:<22s}  {cnt:,}  ({100.0 * cnt / total:.1f}%)")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
