#!/usr/bin/env python3
"""
Memory-safe cleaner for the openFDA Drug Labeling bulk JSON zip files.

This streaming version:
  1. Reads one JSON object at a time from each zip file.
  2. Does NOT store all records in memory.
  3. Uses two passes when keeping only the latest SPL version per set_id.
  4. Writes CSV files incrementally.
  5. Generates a Markdown cleaning report.

Typical usage:
  python clean_openfda_drug_label_bulk_streaming.py \
      --input-dir data/raw \
      --output-dir data/processed \
      --report reports/cleaning_result_report.md

Keep all historical versions:
  python clean_openfda_drug_label_bulk_streaming.py \
      --input-dir data/raw \
      --output-dir data/processed \
      --report reports/cleaning_result_report.md \
      --keep-all-versions
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gc
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

OPENFDA_FIELDS = [
    "application_number", "brand_name", "generic_name", "manufacturer_name",
    "product_ndc", "package_ndc", "product_type", "route", "substance_name",
    "unii", "rxcui", "spl_id", "spl_set_id", "nui", "pharm_class_cs",
    "pharm_class_epc", "pharm_class_moa", "pharm_class_pe", "upc",
    "is_original_packager",
]

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

LONG_OPENFDA_FIELDS = [
    "brand_name", "generic_name", "manufacturer_name", "product_ndc", "package_ndc",
    "product_type", "route", "substance_name", "unii", "rxcui", "application_number"
]

GUID_RE = re.compile(r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$")
NDC_PRODUCT_RE = re.compile(r"^[0-9]{4,5}-[0-9]{3,4}$")
NDC_PACKAGE_RE = re.compile(r"^[0-9]{4,5}-[0-9]{3,4}-[0-9]{1,2}$")
UNII_RE = re.compile(r"^[A-Z0-9]{10}$")
RXCUI_RE = re.compile(r"^[0-9]{1,8}$")
DATE_RE = re.compile(r"^[0-9]{8}$")

MASTER_COLUMNS = (
    [
        "source_file", "record_hash", "id", "set_id", "version",
        "effective_time_raw", "effective_date",
    ]
    + [f"openfda_{f}" for f in OPENFDA_FIELDS]
    + [f"openfda_{f}_count" for f in OPENFDA_FIELDS]
    + TEXT_SECTION_FIELDS
    + [f"{f}_table" for f in TEXT_SECTION_FIELDS]
    + [
        "has_openfda", "has_boxed_warning", "has_adverse_reactions",
        "has_drug_interactions", "has_pregnancy_info", "has_otc_consumer_fields",
        "valid_id_guid", "valid_set_id_guid", "valid_effective_date",
        "valid_product_ndc_format", "valid_package_ndc_format", "valid_unii_format",
        "valid_rxcui_format",
    ]
    + [f"{f}_char_len" for f in [
        "warnings", "boxed_warning", "adverse_reactions", "drug_interactions",
        "indications_and_usage", "description"
    ]]
)

LONG_COLUMNS = ["id", "set_id", "version", "effective_date", "source_file", "openfda_field", "openfda_value"]

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Memory-safe cleaner for openFDA drug label bulk JSON zip files"
    )
    parser.add_argument("--input-dir", required=True, help="Directory containing drug-label-*.json.zip files")
    parser.add_argument("--output-dir", default="data/processed", help="Directory for cleaned CSV outputs")
    parser.add_argument("--report", default="reports/cleaning_result_report.md", help="Markdown report path")
    parser.add_argument("--keep-all-versions", action="store_true", help="Keep every SPL version instead of latest version per set_id")
    parser.add_argument("--encoding", default="utf-8", help="JSON text encoding")
    parser.add_argument("--progress-every", type=int, default=5000, help="Print progress every N records")
    return parser.parse_args()

# -----------------------------------------------------------------------------
# Normalization helpers
# -----------------------------------------------------------------------------


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
    """Convert a scalar/list/dict field into one clean text value."""
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

    seen = set()
    out = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return " | ".join(out)


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


def int_or_none(value: Any) -> Optional[int]:
    try:
        return int(str(value))
    except Exception:
        return None


def make_record_hash(record: Dict[str, Any]) -> str:
    payload = "|".join(str(record.get(k, "")) for k in ["id", "set_id", "version", "effective_time"])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def latest_sort_tuple(record: Dict[str, Any]) -> Tuple[int, str, str]:
    """Sort key for selecting latest record per set_id."""
    version = int_or_none(record.get("version"))
    effective_date = parse_date_yyyymmdd(record.get("effective_time"))
    rid = str(record.get("id", ""))
    return (version if version is not None else -1, effective_date, rid)


def dedup_key(record: Dict[str, Any]) -> str:
    sid = normalize_text_value(record.get("set_id"))
    rid = normalize_text_value(record.get("id"))
    return sid if sid else rid

# -----------------------------------------------------------------------------
# Streaming JSON reader
# -----------------------------------------------------------------------------


def _open_inner_json_text(zip_path: Path, encoding: str) -> io.TextIOWrapper:
    zf = zipfile.ZipFile(zip_path)
    json_names = [name for name in zf.namelist() if name.lower().endswith(".json")]
    if not json_names:
        zf.close()
        raise ValueError(f"No JSON file found inside {zip_path}")
    raw = zf.open(json_names[0])
    # Attach zipfile to stream, so caller can close both by closing wrapper and zipfile manually if needed.
    text = io.TextIOWrapper(raw, encoding=encoding)
    text._openfda_zipfile = zf  # type: ignore[attr-defined]
    return text


def _find_top_level_results_array(text: io.TextIOWrapper) -> str:
    """
    Move the stream cursor to the first character after the opening '[' of the
    top-level `results` array and return the remaining buffer already read.

    We search for the literal pattern '"results": [' instead of the meta.results object,
    because meta.results is an object and appears as '"results": {'.
    """
    pattern = '"results": ['
    buffer = ""
    while True:
        chunk = text.read(1024 * 1024)
        if not chunk:
            raise ValueError("Could not find top-level results array in JSON")
        buffer += chunk
        idx = buffer.find(pattern)
        if idx != -1:
            return buffer[idx + len(pattern):]
        # Keep enough tail for a pattern that may cross chunk boundary.
        buffer = buffer[-len(pattern):]


def iter_records_from_zip(zip_path: Path, encoding: str = "utf-8") -> Iterator[Dict[str, Any]]:
    """
    Yield one record at a time from the top-level results array.

    This avoids json.load(), which would load the entire zip's JSON file into RAM.
    """
    text = _open_inner_json_text(zip_path, encoding)
    zf = getattr(text, "_openfda_zipfile")
    decoder = json.JSONDecoder()
    buffer = ""
    pos = 0
    try:
        buffer = _find_top_level_results_array(text)
        eof = False
        while True:
            # Skip whitespace and commas between records.
            while True:
                while pos < len(buffer) and buffer[pos] in " \r\n\t,":
                    pos += 1
                if pos < len(buffer):
                    break
                more = text.read(1024 * 1024)
                if not more:
                    eof = True
                    break
                buffer = ""
                pos = 0
                buffer += more
            if eof:
                break
            if buffer[pos] == "]":
                break

            # Ensure there is enough buffer to decode one full JSON object.
            while True:
                try:
                    obj, end = decoder.raw_decode(buffer, pos)
                    if isinstance(obj, dict):
                        yield obj
                    pos = end
                    # Trim consumed text to keep memory bounded.
                    if pos > 2 * 1024 * 1024:
                        buffer = buffer[pos:]
                        pos = 0
                    break
                except json.JSONDecodeError:
                    more = text.read(1024 * 1024)
                    if not more:
                        raise
                    buffer += more
    finally:
        try:
            text.close()
        finally:
            zf.close()

# -----------------------------------------------------------------------------
# Cleaning
# -----------------------------------------------------------------------------


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

    for field in OPENFDA_FIELDS:
        row[f"openfda_{field}"] = join_array(openfda.get(field), upper=(field == "unii"))
        row[f"openfda_{field}_count"] = len(normalize_array(openfda.get(field)))

    for field in TEXT_SECTION_FIELDS:
        row[field] = normalize_text_value(record.get(field))
        row[f"{field}_table"] = normalize_text_value(record.get(f"{field}_table"))

    row["has_openfda"] = bool(openfda)
    row["has_boxed_warning"] = bool(row.get("boxed_warning"))
    row["has_adverse_reactions"] = bool(row.get("adverse_reactions"))
    row["has_drug_interactions"] = bool(row.get("drug_interactions"))
    row["has_pregnancy_info"] = bool(row.get("pregnancy"))
    row["has_otc_consumer_fields"] = any(bool(row.get(f)) for f in ["purpose", "do_not_use", "ask_doctor", "stop_use", "when_using"])

    row["valid_id_guid"] = bool(GUID_RE.match(row["id"]))
    row["valid_set_id_guid"] = bool(GUID_RE.match(row["set_id"]))
    row["valid_effective_date"] = bool(row["effective_date"])
    row["valid_product_ndc_format"] = (
        all(NDC_PRODUCT_RE.match(x) for x in normalize_array(openfda.get("product_ndc")))
        if openfda.get("product_ndc") else None
    )
    row["valid_package_ndc_format"] = (
        all(NDC_PACKAGE_RE.match(x) for x in normalize_array(openfda.get("package_ndc")))
        if openfda.get("package_ndc") else None
    )
    row["valid_unii_format"] = (
        all(UNII_RE.match(x.upper()) for x in normalize_array(openfda.get("unii")))
        if openfda.get("unii") else None
    )
    row["valid_rxcui_format"] = (
        all(RXCUI_RE.match(x) for x in normalize_array(openfda.get("rxcui")))
        if openfda.get("rxcui") else None
    )

    for field in ["warnings", "boxed_warning", "adverse_reactions", "drug_interactions", "indications_and_usage", "description"]:
        row[f"{field}_char_len"] = len(row.get(field, ""))

    # Make sure every output column exists.
    for col in MASTER_COLUMNS:
        row.setdefault(col, "")
    return row


def iter_long_rows(row: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    base = {k: row.get(k, "") for k in ["id", "set_id", "version", "effective_date", "source_file"]}
    for field in LONG_OPENFDA_FIELDS:
        val = row.get(f"openfda_{field}", "")
        if not isinstance(val, str) or not val:
            continue
        for item in [x.strip() for x in val.split(";") if x.strip()]:
            out = dict(base)
            out["openfda_field"] = field
            out["openfda_value"] = item
            yield out

# -----------------------------------------------------------------------------
# Stats
# -----------------------------------------------------------------------------


class Stats:
    def __init__(self) -> None:
        self.raw_records = 0
        self.final_records = 0
        self.duplicate_record_hashes = 0
        self.record_hash_seen = set()
        self.multi_version_related_records = 0
        self.set_id_counts = Counter()
        self.source_rows: List[Dict[str, Any]] = []
        self.raw_field_present = Counter()
        self.raw_field_total_seen = Counter()
        self.cleaned_present = Counter()
        self.boolean_true = Counter()
        self.product_type_counts = Counter()
        self.route_counts = Counter()
        self.min_date = ""
        self.max_date = ""

    def add_source(self, source_file: str, zip_size_mb: float, records: int) -> None:
        self.source_rows.append({
            "source_file": source_file,
            "zip_size_mb": zip_size_mb,
            "records": records,
        })

    def observe_raw(self, record: Dict[str, Any]) -> None:
        self.raw_records += 1
        sid = normalize_text_value(record.get("set_id"))
        if sid:
            self.set_id_counts[sid] += 1
        for field, value in record.items():
            self.raw_field_total_seen[field] += 1
            if value not in (None, [], ""):
                self.raw_field_present[field] += 1

    def observe_final_row(self, row: Dict[str, Any]) -> None:
        self.final_records += 1
        date = str(row.get("effective_date", ""))
        if date:
            self.min_date = min(self.min_date, date) if self.min_date else date
            self.max_date = max(self.max_date, date) if self.max_date else date

        for col in MASTER_COLUMNS:
            val = row.get(col, "")
            if val not in (None, [], ""):
                self.cleaned_present[f"cleaned.{col}"] += 1

        for b in [
            "has_openfda", "has_boxed_warning", "has_adverse_reactions",
            "has_drug_interactions", "has_pregnancy_info", "has_otc_consumer_fields",
        ]:
            if bool(row.get(b)):
                self.boolean_true[b] += 1

        for item in [x.strip() for x in str(row.get("openfda_product_type", "")).split(";") if x.strip()]:
            self.product_type_counts[item] += 1
        for item in [x.strip() for x in str(row.get("openfda_route", "")).split(";") if x.strip()]:
            self.route_counts[item] += 1

    def finalize(self) -> None:
        self.multi_version_related_records = sum(c for c in self.set_id_counts.values() if c > 1)

# -----------------------------------------------------------------------------
# Reports and CSV writing
# -----------------------------------------------------------------------------


def write_source_summary(path: Path, stats: Stats) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source_file", "zip_size_mb", "records"])
        writer.writeheader()
        writer.writerows(stats.source_rows)


def write_field_coverage(path: Path, stats: Stats) -> None:
    rows = []
    for field in sorted(stats.raw_field_present):
        present = stats.raw_field_present[field]
        missing = stats.raw_records - present
        rows.append({
            "field": field,
            "present_count": present,
            "missing_count": missing,
            "coverage_pct": round(present / stats.raw_records * 100, 2) if stats.raw_records else 0,
        })
    for col in MASTER_COLUMNS:
        field = f"cleaned.{col}"
        present = stats.cleaned_present.get(field, 0)
        rows.append({
            "field": field,
            "present_count": present,
            "missing_count": stats.final_records - present,
            "coverage_pct": round(present / stats.final_records * 100, 2) if stats.final_records else 0,
        })
    rows.sort(key=lambda r: (-r["coverage_pct"], r["field"]))

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["field", "present_count", "missing_count", "coverage_pct"])
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: List[Dict[str, Any]], columns: List[str], max_rows: Optional[int] = None) -> str:
    if max_rows is not None:
        rows = rows[:max_rows]
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for r in rows:
        body.append("| " + " | ".join(str(r.get(c, "")) for c in columns) + " |")
    return "\n".join([header, sep] + body) if body else header + "\n" + sep


def write_report(path: Path, stats: Stats, keep_all_versions: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_table = markdown_table(stats.source_rows, ["source_file", "zip_size_mb", "records"])
    product_rows = [{"product_type": k, "count": v} for k, v in stats.product_type_counts.most_common(10)]
    route_rows = [{"route": k, "count": v} for k, v in stats.route_counts.most_common(10)]

    bool_pct = lambda name: round(stats.boolean_true.get(name, 0) / stats.final_records * 100, 2) if stats.final_records else 0

    text = f"""# openFDA Drug Labeling Cleaning Report (Memory-Safe Streaming Version)

## 1. Why This Script

The original script loaded all 13 zips into Python lists and pandas DataFrames at once,
causing `zsh: killed` (OOM) around zip 6–7 on macOS. This streaming pipeline reads one
JSON record at a time, cleans it, and writes it directly to CSV — no full dataset in memory.

## 2. Input Files This Run

{source_table}

## 3. Cleaning Strategy

1. Scan each `drug-label-*.json.zip` in sequence.
2. Stream records from the top-level `results` array of each zip's JSON.
3. Extract core version fields: `id`, `set_id`, `version`, `effective_time`.
4. Convert `effective_time` from `YYYYMMDD` to `YYYY-MM-DD`.
5. Flatten `openfda` nested fields to `openfda_*` columns (e.g. `openfda_brand_name`, `openfda_generic_name`).
6. Deduplicate and whitespace-normalize array fields, join with `;`.
7. Clean newlines and repeated whitespace from long-text fields without altering medical meaning.
8. Default: keep only the latest version per `set_id`; use `--keep-all-versions` to retain history.
9. Output master table, long-format table, field coverage table, source summary, and Markdown report.

Current mode: **{'keep all historical versions' if keep_all_versions else 'latest version per set_id'}**.

## 4. Cleaning Summary

| Metric | Value |
|---|---:|
| Raw records read | {stats.raw_records:,} |
| Clean master table rows | {stats.final_records:,} |
| Multi-version set_id related records | {stats.multi_version_related_records:,} |
| Date range | {stats.min_date} to {stats.max_date} |
| Has openfda annotation | {bool_pct('has_openfda')}% |
| Has boxed warning | {bool_pct('has_boxed_warning')}% |
| Has adverse reactions | {bool_pct('has_adverse_reactions')}% |
| Has drug interactions | {bool_pct('has_drug_interactions')}% |
| Has pregnancy info | {bool_pct('has_pregnancy_info')}% |
| Has OTC consumer fields | {bool_pct('has_otc_consumer_fields')}% |

## 5. Product Type — Top 10

{markdown_table(product_rows, ['product_type', 'count'])}

## 6. Route of Administration — Top 10

{markdown_table(route_rows, ['route', 'count'])}

## 7. Output Files

```text
data/processed/
├── clean_label_master.csv
├── openfda_product_long.csv
├── field_coverage.csv
└── source_file_summary.csv
```

## 8. How to Re-run

Keep only latest version (default):

```bash
python clean_openfda_drug_label_bulk_streaming.py \\
    --input-dir data/raw \\
    --output-dir data/processed \\
    --report reports/cleaning_result_report.md
```

Keep all historical versions:

```bash
python clean_openfda_drug_label_bulk_streaming.py \\
    --input-dir data/raw \\
    --output-dir data/processed \\
    --report reports/cleaning_result_report.md \\
    --keep-all-versions
```

## 9. Data Limitations

openFDA Drug Labeling is semi-structured drug label text data. Cleaning only performs
format normalization, version deduplication, field expansion, coverage statistics, and
quality flagging without altering medical meaning. This data must not be used for
medical decision-making.
"""
    path.write_text(text, encoding="utf-8")

# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------


def count_records_in_zip(zip_path: Path, encoding: str, progress_every: int) -> int:
    count = 0
    for _ in iter_records_from_zip(zip_path, encoding):
        count += 1
        if progress_every and count % progress_every == 0:
            print(f"  counted {count:,} records in {zip_path.name}", file=sys.stderr)
    return count


def first_pass(zip_paths: List[Path], args: argparse.Namespace, stats: Stats) -> Dict[str, Tuple[Tuple[int, str, str], str]]:
    """
    First pass finds the latest record_hash per dedup_key and gathers raw stats.
    Returns: dedup_key -> (latest_sort_tuple, record_hash)
    """
    latest_by_key: Dict[str, Tuple[Tuple[int, str, str], str]] = {}

    for zip_path in zip_paths:
        print(f"Pass 1 scanning {zip_path.name} ...", file=sys.stderr)
        records_in_file = 0
        for record in iter_records_from_zip(zip_path, args.encoding):
            records_in_file += 1
            stats.observe_raw(record)

            rh = make_record_hash(record)
            if rh in stats.record_hash_seen:
                stats.duplicate_record_hashes += 1
            else:
                stats.record_hash_seen.add(rh)

            key = dedup_key(record)
            sort_key = latest_sort_tuple(record)
            old = latest_by_key.get(key)
            if old is None or sort_key > old[0]:
                latest_by_key[key] = (sort_key, rh)

            if args.progress_every and records_in_file % args.progress_every == 0:
                print(f"  scanned {records_in_file:,} records", file=sys.stderr)

        stats.add_source(zip_path.name, round(zip_path.stat().st_size / 1024 / 1024, 2), records_in_file)
        gc.collect()

    stats.finalize()
    return latest_by_key


def write_clean_outputs(
    zip_paths: List[Path],
    args: argparse.Namespace,
    output_dir: Path,
    latest_by_key: Dict[str, Tuple[Tuple[int, str, str], str]],
    stats: Stats,
) -> None:
    master_path = output_dir / "clean_label_master.csv"
    long_path = output_dir / "openfda_product_long.csv"

    emitted_latest_keys = set()
    emitted_hashes = set()

    with master_path.open("w", newline="", encoding="utf-8") as master_f, \
         long_path.open("w", newline="", encoding="utf-8") as long_f:

        master_writer = csv.DictWriter(master_f, fieldnames=MASTER_COLUMNS, extrasaction="ignore")
        long_writer = csv.DictWriter(long_f, fieldnames=LONG_COLUMNS, extrasaction="ignore")
        master_writer.writeheader()
        long_writer.writeheader()

        for zip_path in zip_paths:
            print(f"Pass 2 cleaning {zip_path.name} ...", file=sys.stderr)
            records_in_file = 0
            written_in_file = 0

            for record in iter_records_from_zip(zip_path, args.encoding):
                records_in_file += 1
                rh = make_record_hash(record)

                if args.keep_all_versions:
                    # Skip exact duplicate ids/version/effective_time.
                    if rh in emitted_hashes:
                        continue
                    emitted_hashes.add(rh)
                else:
                    key = dedup_key(record)
                    latest = latest_by_key.get(key)
                    if not latest or rh != latest[1]:
                        continue
                    # In rare ties, write latest key only once.
                    if key in emitted_latest_keys:
                        continue
                    emitted_latest_keys.add(key)

                row = clean_record(record, zip_path.name)
                master_writer.writerow(row)
                for long_row in iter_long_rows(row):
                    long_writer.writerow(long_row)
                stats.observe_final_row(row)
                written_in_file += 1

                if args.progress_every and records_in_file % args.progress_every == 0:
                    print(f"  read {records_in_file:,}, wrote {written_in_file:,}", file=sys.stderr)

            gc.collect()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    zip_paths = sorted(input_dir.glob("drug-label-*.json.zip"))
    if not zip_paths:
        raise FileNotFoundError(f"No drug-label-*.json.zip files found in {input_dir}")

    print(f"Found {len(zip_paths)} zip files", file=sys.stderr)
    stats = Stats()

    latest_by_key = first_pass(zip_paths, args, stats)
    write_clean_outputs(zip_paths, args, output_dir, latest_by_key, stats)

    write_source_summary(output_dir / "source_file_summary.csv", stats)
    write_field_coverage(output_dir / "field_coverage.csv", stats)
    write_report(report_path, stats, args.keep_all_versions)

    print("Done.", file=sys.stderr)
    print(f"Clean master: {output_dir / 'clean_label_master.csv'}", file=sys.stderr)
    print(f"Long table:    {output_dir / 'openfda_product_long.csv'}", file=sys.stderr)
    print(f"Report:        {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
