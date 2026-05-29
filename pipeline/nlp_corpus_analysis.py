"""
Corpus-level NLP analysis for the MedInsight homepage visualization.

Methods (from CSEN 377 Week 9):
  - TF-IDF: Each body_part is treated as a "document"; terms come from
      aggregated review_clusters.top_terms.  TF-IDF identifies the words
      that are most *discriminative* for each body system.
  - Full cross-body matrix: for each globally-selected term, compute its
      TF-IDF score across ALL body systems → enables the heatmap visual.
  - Sentiment distribution: aggregate pos/neg/neutral from review_clusters.

Output tables (SQLite):
  corpus_tfidf      (body_part, term, tfidf_score, score_norm, rank)
  corpus_heatmap    (term, body_part, score_norm)  ← full matrix
  corpus_sentiment  (body_part, positive, negative, neutral, total, …_pct)
"""

import json
import math
import sqlite3
from collections import Counter, defaultdict

import pandas as pd

from config import DB_PATH


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_json_list(s: str) -> list[str]:
    if not s:
        return []
    try:
        val = json.loads(s)
        return [v.lower().strip() for v in val if isinstance(v, str) and v.strip()]
    except (json.JSONDecodeError, TypeError):
        return [v.lower().strip() for v in s.split(",") if v.strip()]


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "as", "is", "was", "are", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "it",
    "its", "this", "that", "these", "those", "my", "your", "i", "me",
    "he", "she", "they", "we", "you", "not", "no", "so", "if", "then",
    "than", "just", "also", "very", "more", "some", "any", "all", "such",
    "about", "after", "before", "when", "where", "which", "what", "how",
    "there", "here", "side", "effect", "effects", "drug", "medication",
    "take", "taking", "taken", "use", "using", "used",
    "pain", "feel", "feeling",   # too generic across all body parts
}

# Body-part name tokens to exclude (they appear as their own top terms which is trivial)
_BP_NAME_TOKENS = {
    "brain", "heart", "lung", "lungs", "liver", "stomach", "kidney", "kidneys",
    "skin", "blood", "muscle", "muscles", "ear", "ears", "eye", "eyes",
    "immune", "endocrine", "vascular", "reproductive",
}


# ── TF-IDF ────────────────────────────────────────────────────────────────────

def compute_tfidf(docs: dict[str, list[str]], top_n: int = 15):
    """
    docs  : { body_part → [term, term, …] }  (repetitions = term frequency)
    Returns:
      tfidf_per_bp  : { body_part → [(score, term), …] } sorted desc, top_n each
      tf_all        : { body_part → { term → tf_score } }
      idf           : { term → idf_value }
    """
    N = len(docs)
    tf_all: dict[str, dict[str, float]] = {}
    df: Counter = Counter()

    for bp, terms in docs.items():
        counts = Counter(terms)
        total  = max(sum(counts.values()), 1)
        tf_all[bp] = {t: c / total for t, c in counts.items()}
        for t in counts:
            df[t] += 1

    # IDF: log(N / df)  — terms in ALL docs get idf=0 (uninformative)
    idf: dict[str, float] = {
        t: math.log(N / count)
        for t, count in df.items()
        if 1 <= count < N and t not in STOPWORDS and t not in _BP_NAME_TOKENS
    }

    tfidf_per_bp: dict[str, list[tuple[float, str]]] = {}
    for bp, tf in tf_all.items():
        scored = [(tf[t] * idf[t], t) for t in tf if t in idf]
        scored.sort(reverse=True)
        tfidf_per_bp[bp] = scored[:top_n]

    return tfidf_per_bp, tf_all, idf


# ── main ──────────────────────────────────────────────────────────────────────

def run(db_path=DB_PATH):
    print("▶ Corpus NLP analysis …")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ── 1. Build per-body_part term corpus ────────────────────────────────
    print("  Loading review_clusters …")
    clusters = conn.execute(
        "SELECT body_part, top_terms, review_count FROM review_clusters "
        "WHERE body_part IS NOT NULL AND top_terms IS NOT NULL"
    ).fetchall()

    docs: dict[str, list[str]] = defaultdict(list)
    for row in clusters:
        terms = _parse_json_list(row["top_terms"])
        weight = max(1, int(row["review_count"]) // 5)
        docs[row["body_part"]].extend(terms * weight)

    print(f"  {len(docs)} body parts, {sum(len(v) for v in docs.values()):,} term instances")

    # ── 2. TF-IDF ─────────────────────────────────────────────────────────
    tfidf_per_bp, tf_all, idf = compute_tfidf(dict(docs), top_n=15)

    # Save per-body_part TF-IDF rankings
    global_max = max(
        (s for ranked in tfidf_per_bp.values() for s, _ in ranked),
        default=1.0
    )
    tfidf_rows = []
    for bp, ranked in tfidf_per_bp.items():
        for rank, (score, term) in enumerate(ranked, 1):
            tfidf_rows.append({
                "body_part":   bp,
                "term":        term,
                "tfidf_score": round(score, 6),
                "score_norm":  round(score / global_max, 4),
                "rank":        rank,
            })
    pd.DataFrame(tfidf_rows).to_sql("corpus_tfidf", conn, if_exists="replace", index=False)
    print(f"  ✓ corpus_tfidf: {len(tfidf_rows)} rows")

    # ── 3. Full cross-body heatmap matrix ─────────────────────────────────
    # Select global terms: top-3 per body_part (after filtering)
    global_terms_ordered: list[str] = []
    seen: set[str] = set()
    for bp, ranked in sorted(tfidf_per_bp.items()):
        for _, term in ranked[:3]:
            if term not in seen:
                global_terms_ordered.append(term)
                seen.add(term)

    # For each (global_term × body_part): compute TF-IDF score
    heatmap_rows = []
    for term in global_terms_ordered:
        scores_for_term = []
        for bp in docs:
            tf  = tf_all[bp].get(term, 0.0)
            score = tf * idf.get(term, 0.0)
            scores_for_term.append((bp, score))

        max_score_for_term = max(s for _, s in scores_for_term) or 1.0
        for bp, score in scores_for_term:
            heatmap_rows.append({
                "term":       term,
                "body_part":  bp,
                "score":      round(score, 6),
                "score_norm": round(score / max_score_for_term, 4),
            })

    pd.DataFrame(heatmap_rows).to_sql("corpus_heatmap", conn, if_exists="replace", index=False)
    print(f"  ✓ corpus_heatmap: {len(heatmap_rows)} cells ({len(global_terms_ordered)} terms × {len(docs)} body_parts)")

    # ── 4. Sentiment distribution ─────────────────────────────────────────
    print("  Computing sentiment distribution …")
    sent_raw = conn.execute(
        """
        SELECT body_part, sentiment, SUM(review_count) AS count
        FROM review_clusters
        WHERE body_part IS NOT NULL
        GROUP BY body_part, sentiment
        """
    ).fetchall()

    sent: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    for row in sent_raw:
        bp = row["body_part"]
        s  = row["sentiment"]
        if s in sent[bp]:
            sent[bp][s] = int(row["count"])

    sentiment_out = []
    for bp, counts in sent.items():
        total = max(sum(counts.values()), 1)
        sentiment_out.append({
            "body_part":    bp,
            "positive":     counts["positive"],
            "negative":     counts["negative"],
            "neutral":      counts["neutral"],
            "total":        total,
            "positive_pct": round(counts["positive"] / total * 100, 1),
            "negative_pct": round(counts["negative"] / total * 100, 1),
            "neutral_pct":  round(counts["neutral"]  / total * 100, 1),
        })

    pd.DataFrame(sentiment_out).sort_values("total", ascending=False).to_sql(
        "corpus_sentiment", conn, if_exists="replace", index=False
    )
    print(f"  ✓ corpus_sentiment: {len(sentiment_out)} body parts")

    conn.commit()
    conn.close()
    print("▶ Done.")


if __name__ == "__main__":
    run()
