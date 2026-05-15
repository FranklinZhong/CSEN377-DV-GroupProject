"""
FAERS pipeline: load → clean → SOC-map → write to SQLite (table: faers_events).

Supports two input formats auto-detected by column names:
  A) Combined/Kaggle format  – single CSV with drugname, pt, soc (or soc_name), quarter/fda_dt
  B) Raw FDA quarterly format – folder of DRUG*.txt + REAC*.txt files per quarter
"""

import re
import sqlite3
import pandas as pd
from pathlib import Path

from config import FAERS_DIR, DB_PATH
from soc_body_map import SOC_TO_BODY_PART


# ── helpers ──────────────────────────────────────────────────────────────────

def _normalize_drug_name(name: str) -> str:
    """Uppercase, strip trailing dose/route noise like '10MG' or 'ORAL'."""
    name = str(name).upper().strip()
    name = re.sub(r"\s+\d+\s*MG.*$", "", name)
    name = re.sub(r"\s+(ORAL|IV|TABLET|CAPSULE|SOLUTION|INJECTION).*$", "", name)
    return name.strip()


def _map_soc(soc_name: str) -> str | None:
    if pd.isna(soc_name):
        return None
    # Exact match first, then case-insensitive prefix match
    result = SOC_TO_BODY_PART.get(soc_name)
    if result is not None or soc_name in SOC_TO_BODY_PART:
        return result
    soc_lower = str(soc_name).lower()
    for key, val in SOC_TO_BODY_PART.items():
        if key.lower().startswith(soc_lower[:20]):
            return val
    return None


# ── format A: combined CSV ────────────────────────────────────────────────────

def _load_combined(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = df.columns.str.lower().str.strip()

    col_map = {
        "drug": next((c for c in df.columns if "drug" in c), None),
        "pt":   next((c for c in df.columns if c in ("pt", "reaction_pt", "preferred_term")), None),
        "soc":  next((c for c in df.columns if "soc" in c), None),
        "date": next((c for c in df.columns if c in ("quarter", "fda_dt", "report_date", "date")), None),
    }

    missing = [k for k, v in col_map.items() if v is None and k != "date"]
    if missing:
        raise ValueError(f"Combined CSV missing required columns: {missing}. Found: {list(df.columns)}")

    out = pd.DataFrame({
        "drug_name":  df[col_map["drug"]].map(_normalize_drug_name),
        "pt":         df[col_map["pt"]].str.strip(),
        "soc":        df[col_map["soc"]] if col_map["soc"] else None,
        "quarter":    df[col_map["date"]] if col_map["date"] else None,
    })
    return out


# ── format B: raw FDA quarterly files ────────────────────────────────────────

def _load_raw_quarterly(faers_dir: Path) -> pd.DataFrame:
    drug_files = sorted(faers_dir.glob("DRUG*.txt")) + sorted(faers_dir.glob("drug*.txt"))
    reac_files = sorted(faers_dir.glob("REAC*.txt")) + sorted(faers_dir.glob("reac*.txt"))

    if not drug_files or not reac_files:
        raise FileNotFoundError(
            f"No DRUG*.txt / REAC*.txt files found in {faers_dir}.\n"
            "Download FAERS quarterly data from https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html"
        )

    drug_frames, reac_frames = [], []
    for f in drug_files:
        d = pd.read_csv(f, sep="$", low_memory=False, encoding="latin-1")
        d.columns = d.columns.str.lower().str.strip()
        drug_frames.append(d[["primaryid", "drugname", "role_cod"]])

    for f in reac_files:
        r = pd.read_csv(f, sep="$", low_memory=False, encoding="latin-1")
        r.columns = r.columns.str.lower().str.strip()
        reac_frames.append(r[["primaryid", "pt"]])

    drugs = pd.concat(drug_frames, ignore_index=True)
    reacs = pd.concat(reac_frames, ignore_index=True)

    # Keep only primary suspect drugs
    drugs = drugs[drugs["role_cod"].str.upper() == "PS"]
    merged = reacs.merge(drugs, on="primaryid", how="inner")

    out = pd.DataFrame({
        "drug_name": merged["drugname"].map(_normalize_drug_name),
        "pt":        merged["pt"].str.strip(),
        "soc":       None,   # raw format has no SOC column
        "quarter":   None,
    })
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def run(faers_dir: Path = FAERS_DIR, db_path: Path = DB_PATH) -> int:
    print("▶ FAERS: scanning data directory …")

    csv_files = list(faers_dir.glob("*.csv"))
    if csv_files:
        print(f"  Combined CSV detected: {csv_files[0].name}")
        df = _load_combined(csv_files[0])
    else:
        print("  Raw quarterly format detected.")
        df = _load_raw_quarterly(faers_dir)

    # Drop rows where drug or reaction is missing
    df = df.dropna(subset=["drug_name", "pt"])
    df = df[df["drug_name"].str.len() > 1]

    # Map SOC → body part
    df["body_part"] = df["soc"].map(_map_soc) if df["soc"].notna().any() else None

    # Aggregate: drug × pt × body_part × quarter → count
    group_cols = ["drug_name", "pt", "soc", "body_part", "quarter"]
    agg = (
        df.groupby([c for c in group_cols if c in df.columns and df[c].notna().any()], dropna=False)
        .size()
        .reset_index(name="report_count")
    )

    # Ensure all expected columns exist
    for col in group_cols:
        if col not in agg.columns:
            agg[col] = None

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        agg[group_cols + ["report_count"]].to_sql(
            "faers_events", conn, if_exists="replace", index=False
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_faers_drug ON faers_events(drug_name)")

    n = len(agg)
    print(f"  ✓ {n:,} drug-reaction records written to faers_events")
    return n


if __name__ == "__main__":
    run()
