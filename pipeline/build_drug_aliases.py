"""
build_drug_aliases.py  —  cross-dataset drug name normalization

Problem
-------
FAERS and WebMD drug name overlap is only 15.3% (exact match).
Root causes:
  1. Case differences: FAERS all-caps (METFORMIN) vs WebMD lowercase (metformin)
  2. Brand vs generic: Glucophage vs Metformin
  3. Suffix variants: lisinopril / lisinopril hcl / lisinopril solution
  4. Abbreviations: Humira vs ADALIMUMAB

Solution
--------
1. normalize(): lowercase, strip common suffixes, remove parenthetical content
2. Brand → generic mapping: built-in dictionary of common brand names
3. rapidfuzz fuzzy merge (optional, covers remaining ambiguity)
4. Write to SQLite drug_aliases table

Usage
-----
  python pipeline/build_drug_aliases.py

Output: updates the drug_aliases table in data/processed/medinsight.db
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

# ── Paths ─────────────────────────────────────────────────────────────────────

_BASE    = Path(__file__).parent.parent
_DB      = _BASE / "data" / "processed" / "medinsight.db"
_FAERS   = _BASE / "data" / "processed" / "FAERS" / "cleaned_faers_signals_prr_ror.csv"
_WEBMD   = _BASE / "data" / "processed" / "WebMDReview" / "cleaned_webmd_reviews.csv"

# ── Common suffixes stripped during normalization ─────────────────────────────

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

# ── Brand name → generic name manual mapping (covers most common cases) ──────

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


# ── Core normalization function ───────────────────────────────────────────────

def normalize(name: str) -> str:
    """
    Normalize a drug name:
      1. lowercase
      2. strip parenthetical content (e.g. "warfarin (bulk) 100%")
      3. strip common dosage form / strength suffixes
      4. collapse whitespace
    """
    s = str(name).lower().strip()
    s = re.sub(r"\(.*?\)", "", s)          # strip parenthetical content
    s = _SUFFIX_PATTERN.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_canonical(normalized: str) -> str:
    """Look up generic name via brand mapping; returns original normalized name if not found."""
    return BRAND_TO_GENERIC.get(normalized, normalized)


# ── Build alias table ─────────────────────────────────────────────────────────

def build_aliases() -> list[dict]:
    """
    Read all drug names from FAERS and WebMD, produce alias → canonical_name mapping list.
    """
    aliases: dict[str, tuple[str, float]] = {}  # alias → (canonical, confidence)

    def add(alias: str, canonical: str, confidence: float = 1.0):
        if alias and canonical and alias != canonical:
            aliases[alias] = (canonical, confidence)

    # 1. Brand → generic (manual mapping, confidence=1.0)
    for brand, generic in BRAND_TO_GENERIC.items():
        add(brand, generic, 1.0)

    # 2. FAERS drug name normalized variants
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

    # 3. WebMD drug name normalized variants
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


# ── Write to database ─────────────────────────────────────────────────────────

def write_to_db(alias_rows: list[dict]):
    if not _DB.exists():
        print(f"[WARN] DB not found at {_DB}. Run run_pipeline.py first.")
        return

    conn = sqlite3.connect(_DB)
    conn.execute("DELETE FROM drug_aliases")      # clear before rewrite

    conn.executemany(
        "INSERT INTO drug_aliases (alias, canonical_name, confidence) VALUES (?,?,?)",
        [(r["alias"], r["canonical_name"], r["confidence"]) for r in alias_rows],
    )
    conn.commit()
    conn.close()
    print(f"[OK] {len(alias_rows)} alias rows written to drug_aliases.")


# ── Standalone entry point ────────────────────────────────────────────────────

def main():
    print("Building drug aliases...")
    rows = build_aliases()
    print(f"  Generated {len(rows)} alias mappings.")

    # Brief report
    from collections import Counter
    conf_dist = Counter(round(r["confidence"], 1) for r in rows)
    for conf, cnt in sorted(conf_dist.items(), reverse=True):
        print(f"  confidence={conf}: {cnt} rows")

    write_to_db(rows)


if __name__ == "__main__":
    main()
