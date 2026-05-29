"""
clean_drugs.py — 一次性数据库清理脚本

删除 drugs 表中的非药品条目（过敏原、膳食补充剂、配方代码、OTC 描述性名称等），
并同步清理 effects / review_clusters / search_index / drug_aliases 中的关联记录。

运行方式：
    cd medinsight
    python pipeline/clean_drugs.py
"""

import re
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "processed" / "medinsight.db"

BAD_PATTERNS = [
    re.compile(r'\s+mix$', re.I),                   # "3 weed mix", "common weed mix"
    re.compile(r'pollen', re.I),                     # 花粉提取物
    re.compile(r'ragweed', re.I),                    # 豚草
    re.compile(r'cat\s+hair', re.I),                 # 猫毛过敏原
    re.compile(r'\b(mugwort|bermuda|juglans|carya|agrostis|dactylis|phleum)\b', re.I),
    re.compile(r'dietary\s+supplement', re.I),       # 膳食补充剂
    re.compile(r'hair\s+regrowth', re.I),            # 护发产品
    re.compile(r'^acai\b', re.I),                    # acai 补充剂
    re.compile(r'^\d+[a-z]+-\d+', re.I),            # 配方代码 "20dm-4cpm", "25dph-7.5peh"
    re.compile(
        r',\s*(tablet|capsule|solution|suspension|injection|cream|gel|'
        r'patch|ointment|powder|vial|reconstituted|sublingual|'
        r'effervescent|disintegrating|non-aerosol|non-)',
        re.I,
    ),                                                # 未剥离配方名 "abstral tablet, sublingual"
    re.compile(r'hour\s+(pain|nasal)\s+relief', re.I),  # OTC 描述 "8 hour pain relief"
    re.compile(r',\s*(rectal|chewable|medicated|transdermal|extended\s*release|'
               r'drops|irrigation|inhalation|micronized)', re.I),  # 额外配方描述
    re.compile(r'^\s*alcohol,\s+rubbing\s*$', re.I),  # "alcohol, rubbing" 是 isopropyl alcohol 的别名
    re.compile(r',\s*$', re.I),                        # 尾部逗号（截断/不完整名称）
]


def is_bad(name: str) -> bool:
    if len(name) < 3:
        return True
    return any(p.search(name) for p in BAD_PATTERNS)


def delete_comma_duplicates(conn: sqlite3.Connection) -> int:
    """删除 name 含逗号、且逗号前的 base name 已作为独立条目存在的重复条目。"""
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

    # 1. 找出所有脏条目
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

    # 2. 用占位符批量删除（SQLite 支持 999 个参数上限，分批处理）
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

    # drug_aliases 用 canonical_name 关联（是 name 字符串，不是 id）
    n_aliases = delete_in_batches("drug_aliases", "canonical_name", bad_names)

    n_drugs = delete_in_batches("drugs", "id", bad_ids)

    conn.commit()

    # 3. 删除逗号重复条目（base name 已独立存在的）
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
