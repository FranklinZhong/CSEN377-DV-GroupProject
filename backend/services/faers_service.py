"""
faers_service.py  —  FAERS API 多年季度数据查询 + CUSUM 信号检测

设计思路
--------
本地 FAERS CSV（2024Q4 快照）只用于：
  1. 找出某药的 top-N Preferred Terms（PT_NORM）
  2. 用 BODY_PART_KEYWORDS 映射 PT → body_part

时间演化数据（Vis 2）来自 FDA FAERS API 实时查询：
  GET https://api.fda.gov/drug/event.json?
      search=patient.drug.openfda.generic_name:"metformin"
             AND patient.reaction.reactionmeddrapt:"NAUSEA"
      &count=receivedate&limit=1000

调用流程
--------
get_trend_data(drug_name, drug_id, conn)
  ├─ 检查 api_cache → 命中直接返回
  ├─ _get_top_pts_local()      从本地 CSV 取 top PT
  ├─ _pts_to_body_map()        PT → body_part 分组
  ├─ _fetch_body_timeline()    per body_part 并发 API 请求
  │   └─ _query_faers_api()    → {quarter: count}
  ├─ _fill_missing_quarters()  补齐空季度
  ├─ _cusum_detect()           标注 signal_flag
  └─ 写 api_cache，返回结果
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

# 引入 pipeline 的关键词映射
_PIPELINE = Path(__file__).parent.parent.parent / "pipeline"
sys.path.insert(0, str(_PIPELINE))
from soc_body_map import BODY_PART_KEYWORDS

# 引入缓存工具
from .cache_service import get_cached, set_cached

# ── 常量 ──────────────────────────────────────────────────────────────────────

FAERS_API = "https://api.fda.gov/drug/event.json"
FDA_API_KEY = os.getenv("FDA_API_KEY", "")          # 有 key → 240 req/min，无 → 40 req/min

_FAERS_CSV = (
    Path(__file__).parent.parent.parent
    / "data" / "processed" / "FAERS"
    / "cleaned_faers_signals_prr_ror.csv"
)

# 每个 body_part 最多取几个代表 PT 去查 API
_MAX_PT_PER_BODY = 2
# 时间轴起始年份
_START_YEAR = 2014
# CUSUM slack 倍数（mean 的多少倍算 slack）
_CUSUM_K = 0.5
# CUSUM 触发阈值（超过 mean 的多少倍触发 signal）
_CUSUM_THRESHOLD = 3.0

# SVG 区域映射（与 v3.0 文档第3章一致）
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


# ── 公开入口 ──────────────────────────────────────────────────────────────────

def get_trend_data(drug_name: str, drug_id: int, conn) -> dict:
    """
    主入口：返回 Vis 2 所需的完整时间轴数据。

    返回格式:
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

    # 1. 取本地 top PTs
    top_pts = _get_top_pts_local(drug_name)
    if not top_pts:
        result = {"timeline": [], "signal_events": [],
                  "_warning": "No local FAERS data found for this drug."}
        set_cached(cache_key, result, conn, ttl_days=1)
        return result

    # 2. PT → body_part 分组
    body_pt_map = _pts_to_body_map(top_pts)

    # 3. 并发查 API（每 body_part 取 top-2 PT）
    raw_timelines = asyncio.run(_fetch_all_body_timelines(drug_name, body_pt_map))

    # 4. 组装成统一季度列表
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
                # 计算与前一季度相比的增幅
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


# ── 本地 FAERS 数据（top PT 提取） ───────────────────────────────────────────

def _get_top_pts_local(drug_name: str, top_n: int = 30) -> list[tuple[str, int]]:
    """
    从本地 FAERS CSV 取该药 top-N PT（按 n_reports 降序）。
    返回 [(pt_norm, n_reports), ...]
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
            # 尝试 contains 模糊匹配
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


# ── PT → body_part 分组 ───────────────────────────────────────────────────────

def _pts_to_body_map(top_pts: list[tuple[str, int]]) -> dict[str, list[str]]:
    """
    将 top PT 按 body_part 分组，每组取 top-_MAX_PT_PER_BODY 个。
    返回 {body_part: [pt1, pt2]}
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
        items.sort(reverse=True)  # 按报告数降序
        result[body_part] = [pt for _, pt in items[:_MAX_PT_PER_BODY]]

    return result


# ── FAERS API 查询（异步） ────────────────────────────────────────────────────

async def _fetch_all_body_timelines(
    drug_name: str,
    body_pt_map: dict[str, list[str]],
) -> dict[str, dict[str, int]]:
    """
    并发查询所有 body_part 的 API，合并每个 body_part 下多个 PT 的结果。
    返回 {body_part: {quarter: total_count}}
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
    查询 FDA FAERS API，返回 {quarter: count}。
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


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _date_to_quarter(date_str: str) -> str | None:
    """'20190315' → '2019Q1'"""
    try:
        d = datetime.strptime(date_str[:8], "%Y%m%d")
        q = (d.month - 1) // 3 + 1
        return f"{d.year}Q{q}"
    except Exception:
        return None


def _generate_quarters(start_year: int) -> list[str]:
    """生成从 start_year Q1 到当前季度的所有季度列表。"""
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
    """确保所有季度都有条目，缺失的填 0。"""
    return {q: data.get(q, 0) for q in all_quarters}


def _cusum_detect(counts: list[int]) -> list[bool]:
    """
    简单 CUSUM 单侧检测（上升信号）。
    signal = True 表示该季度累计偏差超过阈值，可能是不良事件爆发。
    """
    n = len(counts)
    if n == 0 or all(c == 0 for c in counts):
        return [False] * n

    reference = sum(counts) / n
    k = reference * _CUSUM_K          # slack：低于 (mean + k) 不累积
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
