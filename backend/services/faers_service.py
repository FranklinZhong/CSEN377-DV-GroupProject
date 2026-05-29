"""
faers_service.py  —  FAERS API multi-year quarterly data query + CUSUM anomaly detection

Design
------
Local FAERS CSV (2024Q4 snapshot) is used only to:
  1. Find top-N Preferred Terms (PT_NORM) for a drug
  2. Map PT → body_part using BODY_PART_KEYWORDS

Time-series data (Vis 2) comes from live FDA FAERS API queries:
  GET https://api.fda.gov/drug/event.json?
      search=patient.drug.openfda.generic_name:"metformin"
             AND patient.reaction.reactionmeddrapt:"NAUSEA"
      &count=receivedate&limit=1000

Call flow
---------
get_trend_data(drug_name, drug_id, conn)
  ├─ check api_cache → return cached result if hit
  ├─ _get_top_pts_local()      load top PTs from local CSV
  ├─ _pts_to_body_map()        group PTs by body_part
  ├─ _fetch_body_timeline()    concurrent API requests per body_part
  │   └─ _query_faers_api()    → {quarter: count}
  ├─ _fill_missing_quarters()  fill empty quarters with zero
  ├─ _cusum_detect()           annotate signal_flag
  └─ write api_cache, return result
"""

import asyncio
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
import pandas as pd

# Import body-part keyword mapping from pipeline
_PIPELINE = Path(__file__).parent.parent.parent / "pipeline"
sys.path.insert(0, str(_PIPELINE))
from soc_body_map import BODY_PART_KEYWORDS

# Import cache utilities
from .cache_service import get_cached, set_cached

# ── Constants ─────────────────────────────────────────────────────────────────

FAERS_API = "https://api.fda.gov/drug/event.json"
FDA_API_KEY = os.getenv("FDA_API_KEY", "")          # with key → 240 req/min, without → 40 req/min

_FAERS_CSV = (
    Path(__file__).parent.parent.parent
    / "data" / "processed" / "FAERS"
    / "cleaned_faers_signals_prr_ror.csv"
)

# Max representative PTs per body_part to query via API
_MAX_PT_PER_BODY = 2
# Timeline start year
_START_YEAR = 2014
# CUSUM slack multiplier (fraction of mean counted as slack)
_CUSUM_K = 0.5
# CUSUM trigger threshold (multiple of mean to trigger signal)
_CUSUM_THRESHOLD = 3.0

# SVG region mapping
_BODY_TO_SVG: dict[str, str] = {
    "brain":       "nervous_system",
    "eye":         "ophthalmologic_system",
    "ear":         "auditory_system",
    "heart":       "cardiovascular_system",
    "lung":        "respiratory_system",
    "stomach":     "digestive_system",
    "liver":       "hepatobiliary_system",
    "kidney":      "renal_system",
    "skin":        "integumentary_system",
    "muscle":      "musculoskeletal_system",
    "blood":       "hematologic_system",
    "vascular":    "vascular_system",
    "endocrine":   "endocrine_system",
    "immune":      "immune_system",
    "reproductive":"reproductive_system",
}


# ── Public entry point ────────────────────────────────────────────────────────

def get_trend_data(drug_name: str, drug_id: int, conn) -> dict:
    """
    Main entry: returns complete timeline data required for Vis 2.

    Return format:
    {
      "timeline": [TrendPoint, ...],
      "signal_events": [SignalEvent, ...]
    }

    TrendPoint = {
      quarter, body_part, svg_region,
      report_count, normalized_frequency,
      signal_flag, missing, confidence
    }
    """
    cache_key = f"faers_trend:v1:{drug_name.lower().strip()}"
    cached = get_cached(cache_key, conn)
    if cached:
        return cached

    # 1. Load top PTs from local FAERS data
    top_pts = _get_top_pts_local(drug_name)
    if not top_pts:
        result = {"timeline": [], "signal_events": [],
                  "_warning": "No local FAERS data found for this drug."}
        set_cached(cache_key, result, conn, ttl_days=1)
        return result

    # 2. Group PTs by body_part
    body_pt_map = _pts_to_body_map(top_pts)

    # 3. Concurrently query API (top-2 PTs per body_part)
    raw_timelines = asyncio.run(_fetch_all_body_timelines(drug_name, body_pt_map))

    # 4. Assemble unified quarterly timeline
    all_quarters = _generate_quarters(_START_YEAR)
    timeline: list[dict] = []
    signal_events: list[dict] = []

    for body_part, quarterly_counts in raw_timelines.items():
        svg_region = _BODY_TO_SVG.get(body_part, body_part)
        filled = _fill_missing_quarters(quarterly_counts, all_quarters)

        counts_list = [filled.get(q, 0) for q in all_quarters]
        signals = _cusum_detect(counts_list)
        max_count = max(counts_list) if any(c > 0 for c in counts_list) else 1

        for i, quarter in enumerate(all_quarters):
            count = counts_list[i]
            is_missing = quarter not in quarterly_counts and count == 0
            norm_freq = round(count / max_count, 4) if max_count > 0 else 0.0
            confidence = _confidence_label(count)

            point = {
                "quarter":              quarter,
                "body_part":            body_part,
                "svg_region":           svg_region,
                "report_count":         count,
                "normalized_frequency": norm_freq,
                "signal_flag":          signals[i],
                "missing":              is_missing,
                "confidence":           confidence,
            }
            timeline.append(point)

            if signals[i] and count > 0:
                # Calculate percent increase vs prior quarter
                prev = counts_list[i - 1] if i > 0 else 0
                increase_pct = (
                    round((count - prev) / prev * 100) if prev > 0 else None
                )
                signal_events.append({
                    "quarter":      quarter,
                    "body_part":    body_part,
                    "report_count": count,
                    "increase_pct": increase_pct,
                })

    result = {"timeline": timeline, "signal_events": signal_events}
    set_cached(cache_key, result, conn, ttl_days=7)
    return result


# ── Local FAERS data (top PT extraction) ─────────────────────────────────────

def _get_top_pts_local(drug_name: str, top_n: int = 30) -> list[tuple[str, int]]:
    """
    Load top-N PTs for a drug from local FAERS CSV (sorted by n_reports desc).
    Returns [(pt_norm, n_reports), ...]
    """
    if not _FAERS_CSV.exists():
        return []

    try:
        df = pd.read_csv(
            _FAERS_CSV,
            usecols=["DRUGNAME_NORM", "PT_NORM", "n_reports"],
        )
        drug_upper = drug_name.upper().strip()
        subset = df[df["DRUGNAME_NORM"].str.upper() == drug_upper]
        if subset.empty:
            # Fall back to contains partial match
            subset = df[df["DRUGNAME_NORM"].str.upper().str.contains(
                re.escape(drug_upper), na=False
            )]
        if subset.empty:
            return []

        top = (
            subset.groupby("PT_NORM")["n_reports"]
            .sum()
            .nlargest(top_n)
            .reset_index()
        )
        return list(zip(top["PT_NORM"], top["n_reports"].astype(int)))
    except Exception:
        return []


# ── PT → body_part grouping ───────────────────────────────────────────────────

def _pts_to_body_map(top_pts: list[tuple[str, int]]) -> dict[str, list[str]]:
    """
    Group top PTs by body_part, keeping top-_MAX_PT_PER_BODY per group.
    Returns {body_part: [pt1, pt2]}
    """
    body_pt_counts: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for pt, count in top_pts:
        pt_lower = pt.lower()
        matched = False
        for body_part, keywords in BODY_PART_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in pt_lower:
                    body_pt_counts[body_part].append((count, pt))
                    matched = True
                    break
            if matched:
                break

    result: dict[str, list[str]] = {}
    for body_part, items in body_pt_counts.items():
        items.sort(reverse=True)  # Sort descending by report count
        result[body_part] = [pt for _, pt in items[:_MAX_PT_PER_BODY]]

    return result


# ── FAERS API query (async) ───────────────────────────────────────────────────

async def _fetch_all_body_timelines(
    drug_name: str,
    body_pt_map: dict[str, list[str]],
) -> dict[str, dict[str, int]]:
    """
    Concurrently query API for all body_parts and merge results across PTs.
    Returns {body_part: {quarter: total_count}}
    """
    tasks = []
    keys = []
    for body_part, pts in body_pt_map.items():
        for pt in pts:
            tasks.append(_query_faers_api(drug_name, pt))
            keys.append(body_part)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for body_part, res in zip(keys, results):
        if isinstance(res, dict):
            for quarter, count in res.items():
                merged[body_part][quarter] += count

    return {bp: dict(qc) for bp, qc in merged.items()}


async def _query_faers_api(drug_name: str, pt: str) -> dict[str, int]:
    """
    Query FDA FAERS API and return {quarter: count}.
    e.g. {"2018Q1": 45, "2019Q3": 82, ...}
    """
    search = (
        f'patient.drug.openfda.generic_name:"{drug_name.lower()}"'
        f' AND patient.reaction.reactionmeddrapt:"{pt.upper()}"'
    )
    # Without an API key the FDA FAERS count endpoint caps at ~100 distinct values;
    # with a key the cap is 1000.  Using a conservative 100 keeps it key-optional.
    params: dict[str, str] = {
        "search": search,
        "count":  "receivedate",
        "limit":  "1000" if FDA_API_KEY else "100",
    }
    if FDA_API_KEY:
        params["api_key"] = FDA_API_KEY

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(FAERS_API, params=params)
        if resp.status_code != 200:
            return {}
        items = resp.json().get("results", [])
    except Exception:
        return {}

    quarterly: dict[str, int] = defaultdict(int)
    for item in items:
        q = _date_to_quarter(str(item.get("time", "")))
        if q:
            quarterly[q] += item.get("count", 0)

    return dict(quarterly)


# ── Utility functions ─────────────────────────────────────────────────────────

def _date_to_quarter(date_str: str) -> str | None:
    """'20190315' → '2019Q1'"""
    try:
        d = datetime.strptime(date_str[:8], "%Y%m%d")
        q = (d.month - 1) // 3 + 1
        return f"{d.year}Q{q}"
    except Exception:
        return None


def _generate_quarters(start_year: int) -> list[str]:
    """Generate all quarters from start_year Q1 to the current quarter."""
    now = datetime.utcnow()
    current_q = (now.month - 1) // 3 + 1
    quarters = []
    for year in range(start_year, now.year + 1):
        for q in range(1, 5):
            if year == now.year and q > current_q:
                break
            quarters.append(f"{year}Q{q}")
    return quarters


def _fill_missing_quarters(
    data: dict[str, int], all_quarters: list[str]
) -> dict[str, int]:
    """Ensure all quarters have an entry; fill missing with 0."""
    return {q: data.get(q, 0) for q in all_quarters}


def _cusum_detect(counts: list[int]) -> list[bool]:
    """
    One-sided CUSUM detection (rising signal).
    signal = True means cumulative deviation exceeded threshold for that quarter.
    """
    n = len(counts)
    if n == 0 or all(c == 0 for c in counts):
        return [False] * n

    reference = sum(counts) / n
    k = reference * _CUSUM_K          # slack: no accumulation below (mean + k)
    threshold = reference * _CUSUM_THRESHOLD

    cumsum = 0.0
    signals = []
    for c in counts:
        cumsum = max(0.0, cumsum + c - reference - k)
        signals.append(cumsum > threshold)
    return signals


def _confidence_label(count: int) -> Literal["high", "medium", "low", "insufficient"]:
    if count >= 50:
        return "high"
    if count >= 10:
        return "medium"
    if count >= 3:
        return "low"
    return "insufficient"
