#!/usr/bin/env python3
"""
Clean openFDA Drug Labeling bulk JSON zip files.

Input:
  data/raw/drug-label-0001-of-0013.json.zip ... drug-label-0013-of-0013.json.zip

Output:
  data/processed/clean_label_master.csv
  data/processed/openfda_product_long.csv
  data/processed/field_coverage.csv
  data/processed/source_file_summary.csv
  reports/cleaning_result_report.md

Usage:
  python clean_openfda_drug_label_bulk.py --input-dir data/raw --output-dir data/processed --report reports/cleaning_result_report.md
  python clean_openfda_drug_label_bulk.py --input-dir /path/to/zips --output-dir output --keep-all-versions

This script is designed for the openFDA /drug/label bulk dataset, where each zip contains
one JSON file with top-level keys: meta and results.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

ID_FIELDS = ["id", "set_id", "version", "effective_time"]

OPENFDA_FIELDS = [
    "application_number", "brand_name", "generic_name", "manufacturer_name",
    "product_ndc", "package_ndc", "product_type", "route", "substance_name",
    "unii", "rxcui", "spl_id", "spl_set_id", "nui", "pharm_class_cs",
    "pharm_class_epc", "pharm_class_moa", "pharm_class_pe", "upc",
    "is_original_packager",
]

# Important label sections selected for an analysis-ready master table.
# The raw field list is much larger; the script keeps all discovered top-level fields in coverage stats.
TEXT_SECTION_FIELDS = [
    "spl_product_data_elements", "active_ingredient", "inactive_ingredient",
    "purpose", "indications_and_usage", "description", "dosage_and_administration",
    "dosage_forms_and_strengths", "contraindications", "warnings", "boxed_warning",
    "precautions", "adverse_reactions", "drug_interactions", "clinical_pharmacology",
    "mechanism_of_action", "pharmacodynamics", "pharmacokinetics", "pregnancy",
    "pediatric_use", "geriatric_use", "overdosage", "how_supplied",
    "storage_and_handling", "package_label_principal_display_panel",
    "spl_unclassified_section", "information_for_patients", "spl_medguide",
    "do_not_use", "ask_doctor", "ask_doctor_or_pharmacist", "stop_use",
    "when_using", "keep_out_of_reach_of_children", "questions",
]

GUID_RE = re.compile(r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$")
NDC_PRODUCT_RE = re.compile(r"^[0-9]{4,5}-[0-9]{3,4}$")
NDC_PACKAGE_RE = re.compile(r"^[0-9]{4,5}-[0-9]{3,4}-[0-9]{1,2}$")
UNII_RE = re.compile(r"^[A-Z0-9]{10}$")
RXCUI_RE = re.compile(r"^[0-9]{1,8}$")
DATE_RE = re.compile(r"^[0-9]{8}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean openFDA drug label bulk JSON zip files")
    parser.add_argument("--input-dir", required=True, help="Directory containing drug-label-*.json.zip files")
    parser.add_argument("--output-dir", default="data/processed", help="Directory for cleaned CSV outputs")
    parser.add_argument("--report", default="reports/cleaning_result_report.md", help="Markdown report path")
    parser.add_argument("--keep-all-versions", action="store_true", help="Keep every SPL version instead of latest version per set_id")
    parser.add_argument("--encoding", default="utf-8", help="JSON text encoding")
    return parser.parse_args()


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text_value(value: Any) -> str:
    """Convert openFDA string/list/table fields into a single clean text value."""
    if value is None:
        return ""
    parts: List[str] = []
    for item in as_list(value):
        if item is None:
            continue
        if isinstance(item, (dict, list)):
            s = json.dumps(item, ensure_ascii=False, sort_keys=True)
        else:
            s = str(item)
        s = normalize_whitespace(s)
        if s:
            parts.append(s)
    # De-duplicate repeated text while preserving order.
    seen = set()
    unique_parts = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            unique_parts.append(p)
    return " | ".join(unique_parts)


def normalize_array(value: Any, upper: bool = False) -> List[str]:
    items = []
    for item in as_list(value):
        if item is None:
            continue
        s = normalize_whitespace(str(item))
        if upper:
            s = s.upper()
        if s:
            items.append(s)
    # de-duplicate preserving order
    seen = set()
    out = []
    for s in items:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def join_array(value: Any, upper: bool = False) -> str:
    return "; ".join(normalize_array(value, upper=upper))


def parse_date_yyyymmdd(value: Any) -> str:
    s = str(value or "").strip()
    if not DATE_RE.match(s):
        return ""
    try:
        return dt.datetime.strptime(s, "%Y%m%d").date().isoformat()
    except ValueError:
        return ""


def int_or_none(value: Any) -> int | None:
    try:
        return int(str(value))
    except Exception:
        return None


def read_zip_records(zip_path: Path, encoding: str = "utf-8") -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    with zipfile.ZipFile(zip_path) as zf:
        json_names = [name for name in zf.namelist() if name.lower().endswith(".json")]
        if not json_names:
            raise ValueError(f"No JSON file found inside {zip_path}")
        if len(json_names) > 1:
            print(f"WARNING: {zip_path.name} contains multiple JSON files; reading {json_names[0]}", file=sys.stderr)
        with zf.open(json_names[0]) as fh:
            data = json.load(fh)
    if "results" not in data:
        raise ValueError(f"{zip_path} does not contain top-level 'results'")
    return data.get("meta", {}), data.get("results", [])


def make_record_hash(record: Dict[str, Any]) -> str:
    # Lightweight stable hash for duplicate tracking. Avoid hashing the full label text,
    # because each SPL record can contain very long sections.
    payload = "|".join(str(record.get(k, "")) for k in ["id", "set_id", "version", "effective_time"])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_record(record: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    openfda = record.get("openfda") or {}
    row: Dict[str, Any] = {
        "source_file": source_file,
        "record_hash": make_record_hash(record),
        "id": normalize_text_value(record.get("id")),
        "set_id": normalize_text_value(record.get("set_id")),
        "version": int_or_none(record.get("version")),
        "effective_time_raw": normalize_text_value(record.get("effective_time")),
        "effective_date": parse_date_yyyymmdd(record.get("effective_time")),
    }

    # openFDA harmonized identifiers and product fields.
    for field in OPENFDA_FIELDS:
        row[f"openfda_{field}"] = join_array(openfda.get(field), upper=(field in {"unii"}))
        row[f"openfda_{field}_count"] = len(normalize_array(openfda.get(field)))

    # Label text sections. Table fields are kept as separate columns when present.
    for field in TEXT_SECTION_FIELDS:
        row[field] = normalize_text_value(record.get(field))
        table_field = f"{field}_table"
        if table_field in record:
            row[table_field] = normalize_text_value(record.get(table_field))

    # Useful binary flags.
    row["has_openfda"] = bool(openfda)
    row["has_boxed_warning"] = bool(row.get("boxed_warning"))
    row["has_adverse_reactions"] = bool(row.get("adverse_reactions"))
    row["has_drug_interactions"] = bool(row.get("drug_interactions"))
    row["has_pregnancy_info"] = bool(row.get("pregnancy"))
    row["has_otc_consumer_fields"] = any(bool(row.get(f)) for f in ["purpose", "do_not_use", "ask_doctor", "stop_use", "when_using"])

    # Data quality validation flags.
    row["valid_id_guid"] = bool(GUID_RE.match(row["id"]))
    row["valid_set_id_guid"] = bool(GUID_RE.match(row["set_id"]))
    row["valid_effective_date"] = bool(row["effective_date"])
    row["valid_product_ndc_format"] = all(NDC_PRODUCT_RE.match(x) for x in normalize_array(openfda.get("product_ndc"))) if openfda.get("product_ndc") else None
    row["valid_package_ndc_format"] = all(NDC_PACKAGE_RE.match(x) for x in normalize_array(openfda.get("package_ndc"))) if openfda.get("package_ndc") else None
    row["valid_unii_format"] = all(UNII_RE.match(x.upper()) for x in normalize_array(openfda.get("unii"))) if openfda.get("unii") else None
    row["valid_rxcui_format"] = all(RXCUI_RE.match(x) for x in normalize_array(openfda.get("rxcui"))) if openfda.get("rxcui") else None

    # Simple text-length diagnostics, useful for detecting empty/abnormally long fields.
    for field in ["warnings", "boxed_warning", "adverse_reactions", "drug_interactions", "indications_and_usage", "description"]:
        row[f"{field}_char_len"] = len(row.get(field, ""))

    return row


def build_openfda_long(master_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    key_cols = ["id", "set_id", "version", "effective_date", "source_file"]
    long_fields = [
        "brand_name", "generic_name", "manufacturer_name", "product_ndc", "package_ndc",
        "product_type", "route", "substance_name", "unii", "rxcui", "application_number"
    ]
    for _, row in master_df.iterrows():
        base = {k: row.get(k) for k in key_cols}
        for field in long_fields:
            val = row.get(f"openfda_{field}", "")
            if not isinstance(val, str) or not val:
                continue
            for item in [x.strip() for x in val.split(";") if x.strip()]:
                out = dict(base)
                out["openfda_field"] = field
                out["openfda_value"] = item
                rows.append(out)
    return pd.DataFrame(rows)


def compute_field_coverage(raw_records: List[Dict[str, Any]], master_df: pd.DataFrame) -> pd.DataFrame:
    top_fields = sorted({k for rec in raw_records for k in rec.keys()})
    rows = []
    n = len(raw_records)
    for field in top_fields:
        present = sum(1 for rec in raw_records if field in rec and rec.get(field) not in (None, [], ""))
        rows.append({"field": field, "present_count": present, "missing_count": n - present, "coverage_pct": round(present / n * 100, 2) if n else 0})
    # Add selected cleaned columns too.
    for col in master_df.columns:
        if col in {"source_file", "record_hash"} or col.endswith("_count") or col.endswith("_char_len"):
            continue
        present = int(master_df[col].notna().sum() - (master_df[col].fillna("").astype(str).str.len() == 0).sum())
        rows.append({"field": f"cleaned.{col}", "present_count": present, "missing_count": len(master_df) - present, "coverage_pct": round(present / len(master_df) * 100, 2) if len(master_df) else 0})
    return pd.DataFrame(rows).sort_values(["coverage_pct", "field"], ascending=[False, True])


def write_report(report_path: Path, master_df: pd.DataFrame, latest_df: pd.DataFrame, source_summary: pd.DataFrame, coverage_df: pd.DataFrame, keep_all_versions: bool) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    n_raw = len(master_df)
    n_clean = len(latest_df)
    duplicated_id = int(master_df.duplicated(subset=["id"]).sum()) if "id" in master_df else 0
    duplicated_set = int(master_df.duplicated(subset=["set_id"], keep=False).sum()) if "set_id" in master_df else 0
    min_date = latest_df["effective_date"].replace("", pd.NA).dropna().min() if "effective_date" in latest_df else ""
    max_date = latest_df["effective_date"].replace("", pd.NA).dropna().max() if "effective_date" in latest_df else ""

    def pct(series: pd.Series) -> float:
        return round(float(series.mean() * 100), 2) if len(series) else 0.0

    product_type_counts = Counter()
    for val in latest_df.get("openfda_product_type", pd.Series(dtype=str)).fillna(""):
        for item in [x.strip() for x in val.split(";") if x.strip()]:
            product_type_counts[item] += 1

    route_counts = Counter()
    for val in latest_df.get("openfda_route", pd.Series(dtype=str)).fillna(""):
        for item in [x.strip() for x in val.split(";") if x.strip()]:
            route_counts[item] += 1

    top_coverage = coverage_df.head(20).to_markdown(index=False)
    source_table = source_summary.to_markdown(index=False)
    prod_table = pd.DataFrame(product_type_counts.most_common(10), columns=["product_type", "count"]).to_markdown(index=False)
    route_table = pd.DataFrame(route_counts.most_common(10), columns=["route", "count"]).to_markdown(index=False)

    text = f"""# openFDA Drug Labeling — Cleaning Report

## 1. Overview

Input: openFDA Drug Labeling bulk dataset (`/drug/label` endpoint), files
`drug-label-0001-of-0013.json.zip` through `drug-label-0013-of-0013.json.zip`.
Each zip contains one JSON file with `meta` and `results`; each result record is a
Structured Product Labeling (SPL) entry.

Outputs:
1. `clean_label_master.csv` — one row per SPL version (or one per `set_id` by default)
2. `openfda_product_long.csv` — brand/generic/NDC/route/substance fields in long format
3. `field_coverage.csv` — field coverage rates before and after cleaning
4. `source_file_summary.csv` — per-zip read statistics
5. `cleaning_result_report.md` — this report

## 2. Input files

{source_table}

## 3. Cleaning strategy

### 3.1 Read and validate

Script reads each `drug-label-*.json.zip`, verifies a `.json` file is present, and
checks that the top-level JSON contains `results`. Each record gets `source_file` and
`record_hash` columns for traceability.

### 3.2 Field normalization

- Core version fields extracted: `id`, `set_id`, `version`, `effective_time`.
- `effective_time` converted from `YYYYMMDD` to ISO `YYYY-MM-DD`.
- Nested `openfda` fields flattened to `openfda_*` columns (e.g. `openfda_brand_name`).
- Array fields deduplicated, whitespace-normalized, joined with `;`.
- Long SPL text sections stripped of redundant whitespace; medical content unchanged.

### 3.3 Deduplication and version selection

SPL labels are living documents; the same `set_id` may have multiple versions. By
default the script keeps the record with the highest `version` / latest `effective_date`
per `set_id`. To retain all versions:

```bash
python pipeline/clean_openfda_bulk.py --input-dir data/raw --output-dir data/processed --keep-all-versions
```

Mode: **{'keep all versions' if keep_all_versions else 'latest version per set_id only'}**

### 3.4 Data quality flags

- `valid_id_guid`, `valid_set_id_guid` — GUID format check
- `valid_effective_date` — date format and parseability
- `valid_product_ndc_format`, `valid_package_ndc_format` — NDC format
- `valid_unii_format`, `valid_rxcui_format` — drug identifier formats
- `has_boxed_warning`, `has_adverse_reactions`, `has_drug_interactions`, `has_pregnancy_info`
- `*_char_len` — text field lengths to detect empty or oversized content

## 4. Summary

| Metric | Value |
|---|---:|
| Raw records read | {n_raw:,} |
| Records in final master table | {n_clean:,} |
| Duplicate ids | {duplicated_id:,} |
| Records from multi-version set_ids | {duplicated_set:,} |
| Date range | {min_date} to {max_date} |
| Has openfda annotation | {pct(latest_df['has_openfda']):.2f}% |
| Has boxed warning | {pct(latest_df['has_boxed_warning']):.2f}% |
| Has adverse reactions | {pct(latest_df['has_adverse_reactions']):.2f}% |
| Has drug interactions | {pct(latest_df['has_drug_interactions']):.2f}% |
| Has pregnancy info | {pct(latest_df['has_pregnancy_info']):.2f}% |
| Has OTC consumer fields | {pct(latest_df['has_otc_consumer_fields']):.2f}% |

## 5. Product Type Top 10

{prod_table}

## 6. Route of Administration Top 10

{route_table}

## 7. Field coverage Top 20

{top_coverage}

## 8. Limitations

openFDA Drug Labeling is semi-structured pharmaceutical label text. This pipeline only
normalizes formats, deduplicates versions, flattens fields, and flags quality issues —
it does not alter the medical meaning of any label. This data must not be used for
clinical decision-making.
"""
    report_path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_paths = sorted(input_dir.glob("drug-label-*.json.zip"))
    if not zip_paths:
        raise FileNotFoundError(f"No drug-label-*.json.zip files found in {input_dir}")

    raw_records: List[Dict[str, Any]] = []
    cleaned_rows: List[Dict[str, Any]] = []
    source_rows = []
    meta_last_updates = []

    for zip_path in zip_paths:
        print(f"Reading {zip_path.name} ...", file=sys.stderr)
        meta, records = read_zip_records(zip_path, args.encoding)
        meta_last_updates.append(str(meta.get("last_updated", "")))
        source_rows.append({
            "source_file": zip_path.name,
            "zip_size_mb": round(zip_path.stat().st_size / 1024 / 1024, 2),
            "records": len(records),
            "meta_last_updated": meta.get("last_updated", ""),
        })
        raw_records.extend(records)
        for rec in records:
            cleaned_rows.append(clean_record(rec, zip_path.name))

    master_df = pd.DataFrame(cleaned_rows)
    source_summary = pd.DataFrame(source_rows)

    # Drop exact duplicate JSON payloads if any.
    master_df = master_df.drop_duplicates(subset=["record_hash"]).copy()

    # Sort for latest version selection.
    master_df["version_sort"] = pd.to_numeric(master_df["version"], errors="coerce").fillna(-1).astype(int)
    master_df["effective_date_sort"] = pd.to_datetime(master_df["effective_date"], errors="coerce")
    master_df = master_df.sort_values(["set_id", "version_sort", "effective_date_sort"], ascending=[True, False, False])

    if args.keep_all_versions:
        final_df = master_df.copy()
    else:
        # Keep one latest row per set_id. Records without set_id are kept by id.
        master_df["dedup_key"] = master_df["set_id"].where(master_df["set_id"].fillna("").astype(str).str.len() > 0, master_df["id"])
        final_df = master_df.drop_duplicates(subset=["dedup_key"], keep="first").copy()

    final_df = final_df.drop(columns=[c for c in ["version_sort", "effective_date_sort", "dedup_key"] if c in final_df.columns])
    all_versions_df = master_df.drop(columns=[c for c in ["version_sort", "effective_date_sort", "dedup_key"] if c in master_df.columns])

    coverage_df = compute_field_coverage(raw_records, final_df)
    openfda_long_df = build_openfda_long(final_df)

    final_df.to_csv(output_dir / "clean_label_master.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    all_versions_df.to_csv(output_dir / "clean_label_all_versions.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    openfda_long_df.to_csv(output_dir / "openfda_product_long.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    coverage_df.to_csv(output_dir / "field_coverage.csv", index=False)
    source_summary.to_csv(output_dir / "source_file_summary.csv", index=False)

    write_report(report_path, all_versions_df, final_df, source_summary, coverage_df, args.keep_all_versions)
    print(f"Done. Clean master: {output_dir / 'clean_label_master.csv'}", file=sys.stderr)
    print(f"Report: {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
