"""
GET /api/corpus/nlp
Serves pre-computed corpus-level NLP data for the homepage visualization:
  - TF-IDF discriminative terms per body system
  - Sentiment distribution per body system
Both are corpus-wide (not drug-specific).
"""

import sqlite3
from fastapi import APIRouter, Depends

from ..db import get_connection
from ..schemas.common import ok, err

router = APIRouter(tags=["corpus"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/api/corpus/nlp")
def corpus_nlp(conn: sqlite3.Connection = Depends(_conn)):
    """
    Returns:
      tfidf   — top terms per body_part ordered by TF-IDF score
      sentiment — pos/neg/neutral distribution per body_part
    """
    try:
        # ── TF-IDF: all terms per body_part (rank <= 15) ───────────────
        tfidf_rows = conn.execute(
            """
            SELECT body_part, term, tfidf_score, score_norm, rank
            FROM corpus_tfidf
            WHERE rank <= 15
            ORDER BY body_part, rank
            """
        ).fetchall()

        tfidf: dict[str, list[dict]] = {}
        for r in tfidf_rows:
            bp = r["body_part"]
            if bp not in tfidf:
                tfidf[bp] = []
            tfidf[bp].append({
                "term":       r["term"],
                "score_norm": r["score_norm"],
                "rank":       r["rank"],
            })

        # ── Sentiment distribution ──────────────────────────────────────
        sent_rows = conn.execute(
            """
            SELECT body_part, positive, negative, neutral, total,
                   positive_pct, negative_pct, neutral_pct
            FROM corpus_sentiment
            ORDER BY total DESC
            """
        ).fetchall()

        sentiment = [
            {
                "body_part":    r["body_part"],
                "positive":     r["positive"],
                "negative":     r["negative"],
                "neutral":      r["neutral"],
                "total":        r["total"],
                "positive_pct": r["positive_pct"],
                "negative_pct": r["negative_pct"],
                "neutral_pct":  r["neutral_pct"],
            }
            for r in sent_rows
        ]

        return ok(
            {"tfidf": tfidf, "sentiment": sentiment},
            source="WebMD + TF-IDF corpus analysis",
            confidence="high",
        )

    except Exception as e:
        return err("CORPUS_NLP_ERROR", str(e))
