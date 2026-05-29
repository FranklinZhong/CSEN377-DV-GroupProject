"""
WebMD pipeline: load → body-part extraction → sentiment → write to SQLite.

Output tables:
  webmd_reviews      – one row per review (drug, condition, rating, sentiment, date)
  webmd_body_parts   – one row per (review_id, body_part) mention
  webmd_summary      – aggregated (drug, body_part, pos_count, neg_count)
"""

import sqlite3
import pandas as pd
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config import WEBMD_DIR, DB_PATH
from soc_body_map import BODY_PART_KEYWORDS


# ── load & normalise columns ──────────────────────────────────────────────────

_COL_ALIASES = {
    "drug_name":  ["drugname", "drug_name", "drug"],
    "condition":  ["condition", "medical_condition"],
    "review":     ["review", "reviews", "comment", "text"],
    "rating":     ["rating", "ratings"],
    "date":       ["date"],
    "useful":     ["usefulcount", "useful_count"],
}

def _find_col(df: pd.DataFrame, key: str) -> str | None:
    for alias in _COL_ALIASES[key]:
        if alias in df.columns:
            return alias
    return None


def _load_webmd(webmd_dir: Path) -> pd.DataFrame:
    csv_files = list(webmd_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV found in {webmd_dir}.\n"
            "Download WebMD Drug Reviews from Kaggle and place the CSV here."
        )

    df = pd.read_csv(csv_files[0], low_memory=False)
    df.columns = df.columns.str.lower().str.strip()

    drug_col   = _find_col(df, "drug_name")
    review_col = _find_col(df, "review")
    if not drug_col or not review_col:
        raise ValueError(f"Cannot find drug/review columns. Found: {list(df.columns)}")

    out = pd.DataFrame()
    out["drug_name"] = df[drug_col].str.upper().str.strip()
    out["review"]    = df[review_col].fillna("").astype(str)

    for key in ("condition", "rating", "date"):
        col = _find_col(df, key)
        out[key] = df[col] if col else None

    out = out.dropna(subset=["drug_name", "review"])
    out = out[out["review"].str.len() > 10]
    out = out.reset_index(drop=True)
    out.index.name = "review_id"
    return out.reset_index()


# ── body-part extraction ──────────────────────────────────────────────────────

def _extract_body_parts(text: str) -> list[str]:
    """Return list of body-part keys mentioned in the review text."""
    text_lower = text.lower()
    found = []
    for part, keywords in BODY_PART_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(part)
    return found


# ── sentiment ─────────────────────────────────────────────────────────────────

_vader = SentimentIntensityAnalyzer()

def _sentiment_label(text: str) -> str:
    score = _vader.polarity_scores(text)["compound"]
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"


# ── main ──────────────────────────────────────────────────────────────────────

def run(webmd_dir: Path = WEBMD_DIR, db_path: Path = DB_PATH) -> int:
    print("▶ WebMD: loading reviews …")
    df = _load_webmd(webmd_dir)
    total = len(df)
    print(f"  {total:,} reviews loaded")

    print("  Running sentiment analysis …")
    df["sentiment"] = df["review"].map(_sentiment_label)

    print("  Extracting body-part mentions …")
    df["body_parts"] = df["review"].map(_extract_body_parts)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        # Table 1: reviews
        df[["review_id", "drug_name", "condition", "rating", "date", "sentiment"]].to_sql(
            "webmd_reviews", conn, if_exists="replace", index=False
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_webmd_drug ON webmd_reviews(drug_name)")

        # Table 2: per-review body-part mentions (exploded)
        mention_rows = [
            {"review_id": row["review_id"], "drug_name": row["drug_name"], "body_part": bp}
            for _, row in df.iterrows()
            for bp in row["body_parts"]
        ]
        if mention_rows:
            pd.DataFrame(mention_rows).to_sql(
                "webmd_body_parts", conn, if_exists="replace", index=False
            )

        # Table 3: summary aggregation (used directly by Vis 3 isotype)
        summary = (
            pd.DataFrame(mention_rows)
            .merge(df[["review_id", "sentiment"]], on="review_id")
            .groupby(["drug_name", "body_part", "sentiment"])
            .size()
            .reset_index(name="count")
            .pivot_table(index=["drug_name", "body_part"], columns="sentiment", values="count", fill_value=0)
            .reset_index()
        )
        # Ensure both columns exist even if all reviews are one-sided
        for col in ("positive", "negative", "neutral"):
            if col not in summary.columns:
                summary[col] = 0
        summary.to_sql("webmd_summary", conn, if_exists="replace", index=False)

    print(f"  ✓ {total:,} reviews processed → webmd_reviews / webmd_body_parts / webmd_summary")
    return total


if __name__ == "__main__":
    run()
