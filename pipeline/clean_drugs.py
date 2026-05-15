"""
clean_drugs.py — One-shot database cleanup script

Removes non-drug entries from the drugs table (allergens, dietary supplements,
formulation codes, OTC descriptive names, etc.) and cascades the deletion to
related records in effects / review_clusters / search_index / drug_aliases.

Usage:
    python pipeline/clean_drugs.py
"""

import re
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "processed" / "medinsight.db"

BAD_PATTERNS = [
    re.compile(r'\s+mix$', re.I),                   # "3 weed mix", "common weed mix"
    re.compile(r'pollen', re.I),                     # pollen extract
    re.compile(r'ragweed', re.I),                    # ragweed allergen
    re.compile(r'cat\s+hair', re.I),                 # cat hair allergen
    re.compile(r'\b(mugwort|bermuda|juglans|carya|agrostis|dactylis|phleum)\b', re.I),
    re.compile(r'dietary\s+supplement', re.I),       # dietary supplement
    re.compile(r'hair\s+regrowth', re.I),            # hair care product
    re.compile(r'^acai\b', re.I),                    # acai supplement
    re.compile(r'^\d+[a-z]+-\d+', re.I),            # formulation codes e.g. "20dm-4cpm"
    re.compile(
        r',\s*(tablet|capsule|solution|suspension|injection|cream|gel|'
        r'patch|ointment|powder|vial|reconstituted|sublingual|'
        r'effervescent|disintegrating|non-aerosol|non-)',
        re.I,
    ),                                                # un-stripped formulation name e.g. "abstral tablet, sublingual"
    re.compile(r'hour\s+(pain|nasal)\s+relief', re.I),  # OTC descriptor e.g. "8 hour pain relief"
    re.compile(r',\s*(rectal|chewable|medicated|transdermal|extended\s*release|'
               r'drops|irrigation|inhalation|micronized)', re.I),  # extra formulation descriptors
    re.compile(r'^\s*alcohol,\s+rubbing\s*$', re.I),  # "alcohol, rubbing" is alias for isopropyl alcohol
    re.compile(r',\s*$', re.I),                        # trailing comma (truncated / incomplete name)
]


def is_bad(name: str) -> bool:
    if len(name) < 3:
        return True
    return any(p.search(name) for p in BAD_PATTERNS)


def delete_comma_duplicates(conn: sqlite3.Connection) -> int:
    """Remove comma-variant entries whose base name already exists as a standalone drug."""
    rows = conn.execute("SELECT id, name FROM drugs WHERE name LIKE '%,%'").fetchall()
    dup_ids = []
    for r in rows:
        base = r["name"].split(",")[0].strip()
        exists = conn.execute(
            "SELECT 1 FROM drugs WHERE name = ? AND id != ?", (base, r["id"])
        ).fetchone()
        if exists:
            dup_ids.append(r["id"])

    if not dup_ids:
        return 0

    ph = ",".join(["?"] * len(dup_ids))
    conn.execute(f"DELETE FROM effects WHERE drug_id IN ({ph})", dup_ids)
    conn.execute(f"DELETE FROM review_clusters WHERE drug_id IN ({ph})", dup_ids)
    conn.execute(f"DELETE FROM search_index WHERE drug_id IN ({ph})", dup_ids)
    conn.execute(f"DELETE FROM drugs WHERE id IN ({ph})", dup_ids)
    return len(dup_ids)


def main():
    if not DB.exists():
        print(f"[ERROR] Database not found: {DB}")
        return

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 1. Find all bad entries
    all_drugs = conn.execute("SELECT id, name FROM drugs").fetchall()
    bad = [(r["id"], r["name"]) for r in all_drugs if is_bad(r["name"])]
    bad_ids = [r[0] for r in bad]
    bad_names = [r[1] for r in bad]

    if not bad_ids:
        print("No bad entries found — database is already clean.")
        conn.close()
        return

    print(f"Found {len(bad_ids)} bad entries out of {len(all_drugs)} total drugs.")
    print("\nSample bad entries:")
    for _, name in bad[:30]:
        print(f"  - {name}")
    if len(bad) > 30:
        print(f"  ... and {len(bad) - 30} more")

    # 2. Batch delete (SQLite supports max ~999 params; process in chunks of 500)
    def delete_in_batches(table: str, col: str, ids: list):
        total = 0
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            placeholders = ",".join(["?"] * len(batch))
            cur = conn.execute(
                f"DELETE FROM {table} WHERE {col} IN ({placeholders})", batch
            )
            total += cur.rowcount
        return total

    print("\nCleaning up related tables...")

    n_effects  = delete_in_batches("effects",         "drug_id", bad_ids)
    n_clusters = delete_in_batches("review_clusters", "drug_id", bad_ids)
    n_index    = delete_in_batches("search_index",    "drug_id", bad_ids)

    # drug_aliases links by name string (canonical_name), not by id
    n_aliases = delete_in_batches("drug_aliases", "canonical_name", bad_names)

    n_drugs = delete_in_batches("drugs", "id", bad_ids)

    conn.commit()

    # 3. Remove comma-variant duplicates (base name already exists as standalone)
    n_dup = delete_comma_duplicates(conn)
    conn.commit()
    conn.close()

    print(f"\nDone!")
    print(f"  drugs deleted (blocklist):    {n_drugs}")
    print(f"  drugs deleted (dup base):     {n_dup}")
    print(f"  effects deleted:              {n_effects}")
    print(f"  review_clusters deleted:      {n_clusters}")
    print(f"  search_index deleted:         {n_index}")
    print(f"  drug_aliases deleted:         {n_aliases}")

    remaining = len(all_drugs) - n_drugs - n_dup
    print(f"\nDatabase now has ~{remaining} drugs.")


if __name__ == "__main__":
    main()
