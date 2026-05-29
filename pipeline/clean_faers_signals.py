"""
clean_faers_signal_dataset.py

Complete data cleaning script for:
FAERS Drug Event Signal Dataset.zip

Input files inside ZIP:
    1. faers_drug_event_counts.csv
    2. faers_signals_prr_ror.csv

Outputs:
    cleaned_faers_drug_event_counts.csv
    cleaned_faers_signals_prr_ror.csv
    faers_cleaning_summary.md

How to run:
    python clean_faers_signal_dataset.py
"""

from pathlib import Path
from zipfile import ZipFile
import re

import numpy as np
import pandas as pd


# =====================================================
# 1. File Paths  (resolved relative to this script so it works from any cwd)
# =====================================================

_HERE = Path(__file__).parent          # medinsight/pipeline/
_DATA = _HERE.parent / "data" / "processed" / "FAERS"

INPUT_ZIP = _DATA / "FAERS Drug Event Signal Dataset.zip"

COUNTS_FILE = "faers_drug_event_counts.csv"
SIGNALS_FILE = "faers_signals_prr_ror.csv"

OUTPUT_COUNTS = _DATA / "cleaned_faers_drug_event_counts.csv"
OUTPUT_SIGNALS = _DATA / "cleaned_faers_signals_prr_ror.csv"
OUTPUT_SUMMARY = _DATA / "faers_cleaning_summary.md"


# =====================================================
# 2. Helper Functions
# =====================================================

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names:
    - strip spaces
    - keep original uppercase style where possible
    """
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df


def clean_text_value(value):
    """
    Clean drug names and adverse event terms:
    - convert missing values to NaN
    - remove extra spaces
    - remove invisible/control characters
    - standardize to uppercase
    """
    if pd.isna(value):
        return np.nan

    value = str(value)
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()

    if value == "" or value.lower() in {"nan", "none", "null"}:
        return np.nan

    return value.upper()


def parse_quarter(qtr):
    """
    Parse FAERS quarter format such as 2024Q4.
    Returns year, quarter, and quarter_start_date.
    """
    if pd.isna(qtr):
        return pd.Series([np.nan, np.nan, pd.NaT])

    qtr = str(qtr).strip().upper()
    match = re.match(r"^(\d{4})Q([1-4])$", qtr)

    if not match:
        return pd.Series([np.nan, np.nan, pd.NaT])

    year = int(match.group(1))
    quarter = int(match.group(2))

    month_map = {
        1: 1,
        2: 4,
        3: 7,
        4: 10
    }

    quarter_start_date = pd.Timestamp(year=year, month=month_map[quarter], day=1)

    return pd.Series([year, quarter, quarter_start_date])


def add_quarter_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add useful quarter-related columns.
    """
    df = df.copy()

    if "QTR" in df.columns:
        df["QTR"] = df["QTR"].astype(str).str.strip().str.upper()
        df[["report_year", "report_quarter", "quarter_start_date"]] = (
            df["QTR"].apply(parse_quarter)
        )

    return df


def validate_non_negative_numeric(df: pd.DataFrame, cols) -> pd.DataFrame:
    """
    Convert columns to numeric and remove invalid negative values.
    """
    df = df.copy()

    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df[(df[col].isna()) | (df[col] >= 0)]

    return df


def basic_quality_report(df: pd.DataFrame, name: str) -> str:
    """
    Build a markdown quality summary for one dataframe.
    """
    report = []
    report.append(f"### {name}")
    report.append("")
    report.append(f"- Rows: {df.shape[0]:,}")
    report.append(f"- Columns: {df.shape[1]:,}")
    report.append(f"- Duplicate rows: {df.duplicated().sum():,}")
    report.append("")
    report.append("#### Missing Values")
    report.append("")
    report.append("| Column | Missing Values |")
    report.append("|---|---:|")

    for col, value in df.isna().sum().items():
        report.append(f"| {col} | {int(value):,} |")

    report.append("")
    return "\n".join(report)


# =====================================================
# 3. Load Data from ZIP
# =====================================================

if not INPUT_ZIP.exists():
    raise FileNotFoundError(
        f"Cannot find {INPUT_ZIP}. "
        "Please place the ZIP file in the same folder as this script."
    )

with ZipFile(INPUT_ZIP, "r") as zip_ref:
    zip_files = zip_ref.namelist()

    if COUNTS_FILE not in zip_files:
        raise FileNotFoundError(f"{COUNTS_FILE} was not found inside the ZIP file.")

    if SIGNALS_FILE not in zip_files:
        raise FileNotFoundError(f"{SIGNALS_FILE} was not found inside the ZIP file.")

    counts_raw = pd.read_csv(zip_ref.open(COUNTS_FILE), low_memory=False)
    signals_raw = pd.read_csv(zip_ref.open(SIGNALS_FILE), low_memory=False)


original_counts_shape = counts_raw.shape
original_signals_shape = signals_raw.shape


# =====================================================
# 4. Clean Drug-Event Counts Table
# =====================================================

counts = counts_raw.copy()
counts = clean_column_names(counts)

required_counts_cols = [
    "DRUGNAME_NORM",
    "QTR",
    "PT_NORM",
    "n_reports",
    "quarter_folder"
]

missing_counts_cols = [col for col in required_counts_cols if col not in counts.columns]
if missing_counts_cols:
    raise ValueError(f"Missing required columns in counts table: {missing_counts_cols}")

# Clean text columns
counts["DRUGNAME_NORM"] = counts["DRUGNAME_NORM"].apply(clean_text_value)
counts["PT_NORM"] = counts["PT_NORM"].apply(clean_text_value)
counts["quarter_folder"] = counts["quarter_folder"].apply(clean_text_value)

# Clean quarter field and add year/quarter features
counts = add_quarter_features(counts)

# Clean numeric count
counts = validate_non_negative_numeric(counts, ["n_reports"])

# Remove rows missing essential identifiers
counts = counts.dropna(subset=["DRUGNAME_NORM", "PT_NORM", "QTR", "n_reports"])

# Remove invalid quarter rows
counts = counts.dropna(subset=["report_year", "report_quarter", "quarter_start_date"])

# Remove exact duplicate rows
counts_duplicate_count = counts.duplicated().sum()
counts = counts.drop_duplicates()

# Aggregate possible duplicate drug-event-quarter rows after cleaning
counts = (
    counts
    .groupby(
        [
            "DRUGNAME_NORM",
            "QTR",
            "PT_NORM",
            "quarter_folder",
            "report_year",
            "report_quarter",
            "quarter_start_date"
        ],
        as_index=False
    )["n_reports"]
    .sum()
)

# Add useful analytical features
counts["drug_event_key"] = counts["DRUGNAME_NORM"] + " | " + counts["PT_NORM"]
counts["log_n_reports"] = np.log1p(counts["n_reports"])


# =====================================================
# 5. Clean PRR/ROR Signals Table
# =====================================================

signals = signals_raw.copy()
signals = clean_column_names(signals)

required_signal_cols = [
    "DRUGNAME_NORM",
    "QTR",
    "PT_NORM",
    "A",
    "B",
    "C",
    "D",
    "PRR",
    "ROR"
]

missing_signal_cols = [col for col in required_signal_cols if col not in signals.columns]
if missing_signal_cols:
    raise ValueError(f"Missing required columns in signals table: {missing_signal_cols}")

# Clean text columns
signals["DRUGNAME_NORM"] = signals["DRUGNAME_NORM"].apply(clean_text_value)
signals["PT_NORM"] = signals["PT_NORM"].apply(clean_text_value)

# Clean quarter field and add time features
signals = add_quarter_features(signals)

# Clean numeric columns
signal_numeric_cols = ["A", "B", "C", "D", "PRR", "ROR"]
signals = validate_non_negative_numeric(signals, signal_numeric_cols)

# Remove rows missing essential identifiers or metrics
signals = signals.dropna(
    subset=[
        "DRUGNAME_NORM",
        "PT_NORM",
        "QTR",
        "A",
        "B",
        "C",
        "D",
        "PRR",
        "ROR"
    ]
)

# Remove invalid quarter rows
signals = signals.dropna(subset=["report_year", "report_quarter", "quarter_start_date"])

# Remove exact duplicate rows
signals_duplicate_count = signals.duplicated().sum()
signals = signals.drop_duplicates()

# Replace infinite values if any exist
signals = signals.replace([np.inf, -np.inf], np.nan)
signals = signals.dropna(subset=["PRR", "ROR"])

# Add signal flags
# Common pharmacovigilance screening rule:
# A >= 3 and PRR >= 2 or ROR >= 2.
signals["PRR_signal"] = (signals["A"] >= 3) & (signals["PRR"] >= 2)
signals["ROR_signal"] = (signals["A"] >= 3) & (signals["ROR"] >= 2)
signals["any_signal"] = signals["PRR_signal"] | signals["ROR_signal"]

# Add useful analytical features
signals["drug_event_key"] = signals["DRUGNAME_NORM"] + " | " + signals["PT_NORM"]
signals["log_PRR"] = np.log1p(signals["PRR"])
signals["log_ROR"] = np.log1p(signals["ROR"])

# Optional: merge n_reports from counts table if available
counts_for_merge = counts[
    ["DRUGNAME_NORM", "QTR", "PT_NORM", "n_reports"]
].copy()

signals = signals.merge(
    counts_for_merge,
    on=["DRUGNAME_NORM", "QTR", "PT_NORM"],
    how="left"
)


# =====================================================
# 6. Final Sort and Save
# =====================================================

counts = counts.sort_values(
    by=["report_year", "report_quarter", "DRUGNAME_NORM", "PT_NORM"]
).reset_index(drop=True)

signals = signals.sort_values(
    by=["report_year", "report_quarter", "DRUGNAME_NORM", "PT_NORM"]
).reset_index(drop=True)

counts.to_csv(OUTPUT_COUNTS, index=False, encoding="utf-8")
signals.to_csv(OUTPUT_SIGNALS, index=False, encoding="utf-8")


# =====================================================
# 7. Generate Cleaning Summary Markdown
# =====================================================

summary = f"""# FAERS Drug Event Signal Dataset Cleaning Summary

## 1. Input Dataset

Input ZIP file:

```text
{INPUT_ZIP}
```

Files detected and processed:

```text
{COUNTS_FILE}
{SIGNALS_FILE}
```

---

## 2. Original Dataset Size

| Table | Rows | Columns |
|---|---:|---:|
| Drug-event counts | {original_counts_shape[0]:,} | {original_counts_shape[1]:,} |
| PRR/ROR signals | {original_signals_shape[0]:,} | {original_signals_shape[1]:,} |

---

## 3. Cleaning Actions Applied

### Drug-event counts table

1. Loaded CSV from ZIP.
2. Standardized column names.
3. Cleaned `DRUGNAME_NORM`, `PT_NORM`, and `quarter_folder`.
4. Standardized `QTR` format.
5. Parsed quarter into:
   - `report_year`
   - `report_quarter`
   - `quarter_start_date`
6. Converted `n_reports` to numeric.
7. Removed negative or invalid report counts.
8. Removed rows missing essential identifiers.
9. Removed invalid quarter rows.
10. Removed exact duplicate rows.
11. Aggregated duplicate drug-event-quarter records after cleaning.
12. Added:
   - `drug_event_key`
   - `log_n_reports`

### PRR/ROR signal table

1. Loaded CSV from ZIP.
2. Standardized column names.
3. Cleaned `DRUGNAME_NORM` and `PT_NORM`.
4. Standardized `QTR` format.
5. Parsed quarter into:
   - `report_year`
   - `report_quarter`
   - `quarter_start_date`
6. Converted `A`, `B`, `C`, `D`, `PRR`, and `ROR` to numeric.
7. Removed negative or invalid numeric values.
8. Removed rows missing essential identifiers or signal metrics.
9. Removed infinite PRR/ROR values.
10. Removed exact duplicate rows.
11. Added signal flags:
   - `PRR_signal`
   - `ROR_signal`
   - `any_signal`
12. Added:
   - `drug_event_key`
   - `log_PRR`
   - `log_ROR`
13. Merged `n_reports` from the cleaned counts table.

---

## 4. Duplicate Records Removed

| Table | Exact Duplicate Rows Before Final Cleaning |
|---|---:|
| Drug-event counts | {counts_duplicate_count:,} |
| PRR/ROR signals | {signals_duplicate_count:,} |

---

## 5. Final Dataset Size

| Output File | Rows | Columns |
|---|---:|---:|
| `{OUTPUT_COUNTS}` | {counts.shape[0]:,} | {counts.shape[1]:,} |
| `{OUTPUT_SIGNALS}` | {signals.shape[0]:,} | {signals.shape[1]:,} |

---

## 6. Final Data Quality Report

{basic_quality_report(counts, "Cleaned Drug-Event Counts Table")}

{basic_quality_report(signals, "Cleaned PRR/ROR Signals Table")}

---

## 7. Output Files

```text
{OUTPUT_COUNTS}
{OUTPUT_SIGNALS}
{OUTPUT_SUMMARY}
```

---

## 8. Important Interpretation Note

FAERS is a spontaneous adverse-event reporting system.  
The signal metrics in this dataset, such as PRR and ROR, indicate disproportional reporting patterns.  
They do not prove that a drug caused an adverse event.

Use this cleaned dataset for exploratory analysis, signal screening, visualization, and machine learning tasks, but avoid making direct medical causality claims.
"""

OUTPUT_SUMMARY.write_text(summary, encoding="utf-8")


print("FAERS data cleaning completed successfully.")
print(f"Saved: {OUTPUT_COUNTS}")
print(f"Saved: {OUTPUT_SIGNALS}")
print(f"Saved: {OUTPUT_SUMMARY}")
