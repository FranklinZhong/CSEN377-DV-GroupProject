"""
build_drug_aliases.py  —  跨数据集药品名标准化

问题背景
--------
FAERS 和 WebMD 的药品名重叠率只有 15.3%（精确匹配）。
主要原因：
  1. 大小写不同：FAERS 全大写（METFORMIN），WebMD 小写（metformin）
  2. 品牌名 vs 通用名：Glucophage vs Metformin
  3. 后缀变体：lisinopril / lisinopril hcl / lisinopril solution
  4. 缩写/简称：Humira vs ADALIMUMAB

解决方案
--------
1. 归一化（normalize）：统一小写，去除常见后缀，去括号内容
2. 品牌→通用名映射：内置常见品牌名字典
3. 用 rapidfuzz 做模糊合并（可选，覆盖剩余歧义）
4. 写入 SQLite drug_aliases 表

运行方式
--------
  python pipeline/build_drug_aliases.py

输出：更新 data/processed/medinsight.db 中的 drug_aliases 表
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

# ── 路径 ──────────────────────────────────────────────────────────────────────

_BASE    = Path(__file__).parent.parent
_DB      = _BASE / "data" / "processed" / "medinsight.db"
_FAERS   = _BASE / "data" / "processed" / "FAERS" / "cleaned_faers_signals_prr_ror.csv"
_WEBMD   = _BASE / "data" / "processed" / "WebMDReview" / "cleaned_webmd_reviews.csv"

# ── 常见后缀（规范化时去除） ──────────────────────────────────────────────────

_SUFFIX_PATTERN = re.compile(
    r"\s+("
    r"hcl|hydrochloride|sodium|potassium|sulfate|sulphate|"
    r"maleate|tartrate|fumarate|succinate|acetate|citrate|"
    r"er|xl|xr|sr|cr|ir|cd|la|sa|dr|"          # extended-release variants
    r"solution|suspension|tablet|capsule|patch|"
    r"powder|bulk|injection|infusion|cream|gel|"
    r"oral|topical|iv|im|"
    r"\d+\s*mg|\d+\s*%"                          # dosage/concentration
    r")(\s+.*)?$",
    re.IGNORECASE,
)

# ── 品牌名 → 通用名 手工映射（覆盖最常见情况） ───────────────────────────────

BRAND_TO_GENERIC: dict[str, str] = {
    # Diabetes
    "glucophage":      "metformin",
    "ozempic":         "semaglutide",
    "victoza":         "liraglutide",
    "jardiance":       "empagliflozin",
    "farxiga":         "dapagliflozin",
    "trulicity":       "dulaglutide",
    "lantus":          "insulin glargine",
    "humalog":         "insulin lispro",
    "novolog":         "insulin aspart",
    # Cardiovascular
    "lipitor":         "atorvastatin",
    "zocor":           "simvastatin",
    "crestor":         "rosuvastatin",
    "norvasc":         "amlodipine",
    "toprol":          "metoprolol",
    "lopressor":       "metoprolol",
    "coreg":           "carvedilol",
    "lasix":           "furosemide",
    "coumadin":        "warfarin",
    "xarelto":         "rivaroxaban",
    "eliquis":         "apixaban",
    "plavix":          "clopidogrel",
    "prinivil":        "lisinopril",
    "zestril":         "lisinopril",
    "altace":          "ramipril",
    "vasotec":         "enalapril",
    "diovan":          "valsartan",
    "cozaar":          "losartan",
    # Mental health
    "prozac":          "fluoxetine",
    "zoloft":          "sertraline",
    "lexapro":         "escitalopram",
    "celexa":          "citalopram",
    "effexor":         "venlafaxine",
    "cymbalta":        "duloxetine",
    "wellbutrin":      "bupropion",
    "abilify":         "aripiprazole",
    "seroquel":        "quetiapine",
    "risperdal":       "risperidone",
    "xanax":           "alprazolam",
    "ativan":          "lorazepam",
    "klonopin":        "clonazepam",
    "ambien":          "zolpidem",
    "lunesta":         "eszopiclone",
    # Pain / anti-inflammatory
    "advil":           "ibuprofen",
    "motrin":          "ibuprofen",
    "aleve":           "naproxen",
    "tylenol":         "acetaminophen",
    "celebrex":        "celecoxib",
    "lyrica":          "pregabalin",
    "neurontin":       "gabapentin",
    "ultram":          "tramadol",
    "vicodin":         "hydrocodone",
    "percocet":        "oxycodone",
    "oxycontin":       "oxycodone",
    # Antibiotics
    "zithromax":       "azithromycin",
    "augmentin":       "amoxicillin-clavulanate",
    "levaquin":        "levofloxacin",
    "cipro":           "ciprofloxacin",
    "flagyl":          "metronidazole",
    "diflucan":        "fluconazole",
    # Biologics / specialty
    "humira":          "adalimumab",
    "enbrel":          "etanercept",
    "remicade":        "infliximab",
    "inflectra":       "infliximab",
    "rituxan":         "rituximab",
    "herceptin":       "trastuzumab",
    "avastin":         "bevacizumab",
    "keytruda":        "pembrolizumab",
    "opdivo":          "nivolumab",
    "dupixent":        "dupilumab",
    "stelara":         "ustekinumab",
    "skyrizi":         "risankizumab",
    # GI
    "nexium":          "esomeprazole",
    "prilosec":        "omeprazole",
    "prevacid":        "lansoprazole",
    "protonix":        "pantoprazole",
    "zantac":          "ranitidine",
    "pepcid":          "famotidine",
    # Other common
    "synthroid":       "levothyroxine",
    "armour thyroid":  "thyroid desiccated",
    "prednisone":      "prednisone",  # same, explicit
    "medrol":          "methylprednisolone",
    "decadron":        "dexamethasone",
    "lasix":           "furosemide",
    "aldactone":       "spironolactone",
    "singular":        "montelukast",
    "singulair":       "montelukast",
    "allegra":         "fexofenadine",
    "zyrtec":          "cetirizine",
    "claritin":        "loratadine",
    "adderall":        "amphetamine",
    "ritalin":         "methylphenidate",
    "concerta":        "methylphenidate",
    "strattera":       "atomoxetine",
    "topamax":         "topiramate",
    "lamictal":        "lamotrigine",
    "keppra":          "levetiracetam",
    "dilantin":        "phenytoin",
    "methotrexate":    "methotrexate",  # same
    "actonel":         "risedronate",
    "fosamax":         "alendronate",
    "boniva":          "ibandronate",
    "prolia":          "denosumab",
    "trelegy":         "fluticasone-umeclidinium-vilanterol",
    "spiriva":         "tiotropium",
    "symbicort":       "budesonide-formoterol",
    "advair":          "fluticasone-salmeterol",
    "flovent":         "fluticasone",
}


# ── 核心规范化函数 ────────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    """
    统一药品名：
      1. 小写
      2. 去括号内容（如 "warfarin (bulk) 100%"）
      3. 去常见剂型/剂量后缀
      4. 去多余空格
    """
    s = str(name).lower().strip()
    s = re.sub(r"\(.*?\)", "", s)          # 去括号内容
    s = _SUFFIX_PATTERN.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_canonical(normalized: str) -> str:
    """通过品牌名映射找通用名；找不到就返回原规范化名。"""
    return BRAND_TO_GENERIC.get(normalized, normalized)


# ── 构建别名表 ────────────────────────────────────────────────────────────────

def build_aliases() -> list[dict]:
    """
    读取 FAERS 和 WebMD 的全部药品名，生成 alias → canonical_name 的映射列表。
    """
    aliases: dict[str, tuple[str, float]] = {}  # alias → (canonical, confidence)

    def add(alias: str, canonical: str, confidence: float = 1.0):
        if alias and canonical and alias != canonical:
            aliases[alias] = (canonical, confidence)

    # 1. 品牌名 → 通用名（手工映射，confidence=1.0）
    for brand, generic in BRAND_TO_GENERIC.items():
        add(brand, generic, 1.0)

    # 2. FAERS 药品名规范化变体
    if _FAERS.exists():
        faers_names = pd.read_csv(_FAERS, usecols=["DRUGNAME_NORM"])["DRUGNAME_NORM"].unique()
        for raw in faers_names:
            norm = normalize(raw)
            canonical = to_canonical(norm)
            original_lower = raw.lower().strip()
            if original_lower != canonical:
                add(original_lower, canonical, 0.95)
            if norm != canonical:
                add(norm, canonical, 0.95)

    # 3. WebMD 药品名规范化变体
    if _WEBMD.exists():
        webmd_names = pd.read_csv(_WEBMD, usecols=["Drug"])["Drug"].unique()
        for raw in webmd_names:
            norm = normalize(raw)
            canonical = to_canonical(norm)
            original_lower = raw.lower().strip()
            if original_lower != canonical:
                add(original_lower, canonical, 0.9)
            if norm != canonical:
                add(norm, canonical, 0.9)

    return [
        {"alias": alias, "canonical_name": canon, "confidence": conf}
        for alias, (canon, conf) in aliases.items()
    ]


# ── 写入数据库 ────────────────────────────────────────────────────────────────

def write_to_db(alias_rows: list[dict]):
    if not _DB.exists():
        print(f"[WARN] DB not found at {_DB}. Run run_pipeline.py first.")
        return

    conn = sqlite3.connect(_DB)
    conn.execute("DELETE FROM drug_aliases")      # 清空后重写

    conn.executemany(
        "INSERT INTO drug_aliases (alias, canonical_name, confidence) VALUES (?,?,?)",
        [(r["alias"], r["canonical_name"], r["confidence"]) for r in alias_rows],
    )
    conn.commit()
    conn.close()
    print(f"[OK] {len(alias_rows)} alias rows written to drug_aliases.")


# ── 独立运行入口 ──────────────────────────────────────────────────────────────

def main():
    print("Building drug aliases...")
    rows = build_aliases()
    print(f"  Generated {len(rows)} alias mappings.")

    # 简单报告
    from collections import Counter
    conf_dist = Counter(round(r["confidence"], 1) for r in rows)
    for conf, cnt in sorted(conf_dist.items(), reverse=True):
        print(f"  confidence={conf}: {cnt} rows")

    write_to_db(rows)


if __name__ == "__main__":
    main()
