"""
aggregate_rating.py — Aggregate WebMD review ratings into drugs.overall_rating

Computes the mean of reviews.rating per drug and writes it back to
drugs.overall_rating for all drugs that have at least one rated review.

Usage:
    python pipeline/aggregate_rating.py
"""

import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "processed" / "medinsight.db"


def aggregate(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.cursor()

    before = cur.execute(
        "SELECT COUNT(*) FROM drugs WHERE overall_rating IS NOT NULL"
    ).fetchone()[0]

    cur.execute(
        """
        UPDATE drugs
        SET overall_rating = (
            SELECT ROUND(AVG(r.rating), 2)
            FROM reviews r
            WHERE r.drug_id = drugs.id
              AND r.rating IS NOT NULL
        )
        WHERE id IN (
            SELECT DISTINCT drug_id FROM reviews WHERE rating IS NOT NULL
        )
        """
    )
    updated = cur.rowcount
    conn.commit()

    after = cur.execute(
        "SELECT COUNT(*) FROM drugs WHERE overall_rating IS NOT NULL"
    ).fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]

    return {"before": before, "after": after, "updated": updated, "total": total}


def main():
    print("=" * 55)
    print("  Aggregate Rating: reviews.rating → drugs.overall_rating")
    print("=" * 55)

    conn = sqlite3.connect(DB)
    try:
        stats = aggregate(conn)
        pct = 100.0 * stats["after"] / stats["total"] if stats["total"] else 0
        print(f"  drugs total            : {stats['total']:,}")
        print(f"  with rating (before)   : {stats['before']:,}")
        print(f"  with rating (after)    : {stats['after']:,}  ({pct:.1f}%)")
        print(f"  rows updated           : {stats['updated']:,}")

        sample = conn.execute(
            "SELECT name, overall_rating FROM drugs "
            "WHERE overall_rating IS NOT NULL "
            "ORDER BY id LIMIT 5"
        ).fetchall()
        print("\n  Sample:")
        for name, rating in sample:
            print(f"    {name:<40s}  ★ {rating}")
    finally:
        conn.close()

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
