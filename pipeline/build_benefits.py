"""
build_benefits.py — 从 indication_summary 文本派生 benefits 数据

v3.5 修复：effects 表 effect_type='benefit' 为 0 条，BodyMap 无法显示绿色高亮。

逻辑
----
1. 读取 drugs 表里 indication_summary 非空的药品
2. 对 indication 文本 + mechanism_of_action 应用 BODY_PART_KEYWORDS 关键词匹配
3. 命中的 body_part 视为该药对那个身体部位"有益"
4. INSERT INTO effects (effect_type='benefit', source='FDA Label', confidence='medium')

注意
----
- 不删除现有 side_effect 记录，只清理 effect_type='benefit' source='FDA Label'
- severity 统一 'low'（治疗作用本身不是严重程度概念）
- frequency = 该 body_part 在 indication 文本中的关键词出现次数（归一化 0-1）

运行
----
  python pipeline/build_benefits.py
"""

import re
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from soc_body_map import BODY_PART_KEYWORDS  # noqa: E402

_DB = Path(__file__).parent.parent / "data" / "processed" / "medinsight.db"

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


_BENEFIT_EXTRA = {
    "brain":        ["neurological", "psychiatric", "anti-epileptic", "antidepressant"],
    "heart":        ["cardiovascular", "antihypertensive", "antianginal"],
    "lung":         ["pulmonary", "antiasthmatic", "bronchodilator"],
    "stomach":      ["gastrointestinal", "antiemetic", "antidiarrhoeal", "laxative"],
    "liver":        ["hepatobiliary"],
    "kidney":       ["renal", "urological", "diuretic"],
    "skin":         ["dermatological", "topical"],
    "muscle":       ["musculoskeletal", "antiinflammatory", "anti-inflammatory",
                     "analgesic", "antirheumatic"],
    "blood":        ["anticoagulant", "antiplatelet", "thrombolytic", "haematological"],
    "vascular":     ["vasodilator"],
    "endocrine":    ["endocrine", "antidiabetic", "antithyroid", "corticosteroid",
                     "glycemic control", "glucose"],
    "immune":       ["immunosuppressant", "immunomodulator", "anti-infective",
                     "antibiotic", "antifungal", "antiviral"],
    "reproductive": ["contraceptive", "obstetric", "gynaecologic"],
    "eye":          ["ophthalmic"],
    "ear":          ["otic"],
}


def _extract_benefits(text: str) -> dict[str, int]:
    """
    Return {body_part: hit_count} for keywords found in `text`.
    Skips negative-effect-only keywords (e.g. "pain", "headache", "nausea")
    that don't represent "drug helps X" semantics.
    """
    t = text.lower()
    counts: dict[str, int] = {}

    # Tokens that, when matched, almost certainly indicate a side-effect
    # context, not a therapeutic indication
    SE_ONLY = {
        "headache", "migraine", "dizziness", "nausea", "vomit", "vomiting",
        "diarrhoea", "diarrhea", "rash", "pruritus", "alopecia", "fatigue",
        "asthenia", "constipation",
    }

    for body_part, kws in BODY_PART_KEYWORDS.items():
        hit = 0
        all_kws = list(kws) + _BENEFIT_EXTRA.get(body_part, [])
        # body_part name itself is a strong signal when present in indication
        all_kws.append(body_part)
        for kw in all_kws:
            kwl = kw.lower()
            if kwl in SE_ONLY:
                continue
            # word-boundary count for short kws, substring for long
            if len(kwl) <= 4:
                pattern = r"\b" + re.escape(kwl) + r"\b"
                hit += len(re.findall(pattern, t))
            else:
                hit += t.count(kwl)
        if hit:
            counts[body_part] = hit
    return counts


def build(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM effects "
        "WHERE effect_type = 'benefit' AND source IN ('FDA Label', 'FDA')"
    )
    removed = cur.rowcount

    cols = {r[1] for r in cur.execute("PRAGMA table_info(drugs)").fetchall()}
    select_cols = ["id", "name", "indication_summary"]
    if "mechanism_of_action" in cols:
        select_cols.append("mechanism_of_action")

    rows = cur.execute(
        f"SELECT {', '.join(select_cols)} FROM drugs "
        "WHERE indication_summary IS NOT NULL AND TRIM(indication_summary) != ''"
    ).fetchall()
    print(f"  Drugs with indication text : {len(rows):,}")

    benefit_rows: list[tuple] = []
    drugs_with_benefits = 0
    total_parts = 0

    for row in rows:
        drug_id = row[0]
        indication = row[2] or ""
        mech = row[3] if len(row) > 3 else ""
        text = f"{indication}  {mech or ''}"

        counts = _extract_benefits(text)
        if not counts:
            continue

        drugs_with_benefits += 1
        total = sum(counts.values()) or 1
        for body_part, n in counts.items():
            total_parts += 1
            freq = round(n / total, 3)
            effect_name = f"Indicated for {body_part}-related conditions"
            benefit_rows.append((
                drug_id, body_part, _BODY_TO_SVG.get(body_part, body_part),
                effect_name, "benefit", "low",
                "FDA Label", freq, "medium",
                "Derived from FDA Drug Label indications text."
            ))

    cur.executemany(
        "INSERT INTO effects "
        "(drug_id, body_part, svg_region, effect_name, effect_type, severity, "
        " source, frequency, confidence, description) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        benefit_rows,
    )
    conn.commit()

    return {
        "removed": removed,
        "drugs_with_benefits": drugs_with_benefits,
        "benefit_rows_inserted": len(benefit_rows),
        "avg_parts_per_drug": total_parts / max(drugs_with_benefits, 1),
    }


def main():
    print("=" * 55)
    print("  Build Benefits from indication_summary text")
    print("=" * 55)

    conn = sqlite3.connect(_DB)
    try:
        stats = build(conn)
        total_drugs = conn.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
        print(f"\n  removed (old benefits)      : {stats['removed']:,}")
        print(f"  drugs with new benefits      : {stats['drugs_with_benefits']:,}  "
              f"({100.0 * stats['drugs_with_benefits'] / total_drugs:.1f}%)")
        print(f"  total benefit rows inserted  : {stats['benefit_rows_inserted']:,}")
        print(f"  avg body_parts per drug      : {stats['avg_parts_per_drug']:.2f}")

        # sample
        sample = conn.execute(
            "SELECT d.name, e.body_part, e.frequency, e.effect_name "
            "FROM effects e JOIN drugs d ON e.drug_id = d.id "
            "WHERE e.effect_type = 'benefit' AND d.name = 'metformin' "
            "ORDER BY e.frequency DESC"
        ).fetchall()
        if sample:
            print(f"\n  Sample (metformin):")
            for name, bp, freq, eff in sample:
                print(f"    {bp:<12s}  freq={freq}  {eff}")
    finally:
        conn.close()

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
