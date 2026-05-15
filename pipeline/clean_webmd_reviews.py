"""
clean_webmd_reviews.py

Data cleaning script for the WebMD Drug Reviews Dataset.

Input:
    WebMD Drug Reviews Dataset.zip

Output:
    cleaned_webmd_reviews.csv
    cleaning_summary.txt

How to run:
    python clean_webmd_reviews.py
"""

import re
import zipfile
from pathlib import Path

import pandas as pd


# =========================
# 1. File Paths  (resolved relative to this script so it works from any cwd)
# =========================

_HERE = Path(__file__).parent          # medinsight/pipeline/
_DATA = _HERE.parent / "data" / "processed" / "WebMDReview"

INPUT_ZIP   = _DATA / "WebMD Drug Reviews Dataset.zip"
OUTPUT_CSV  = _DATA / "cleaned_webmd_reviews.csv"
SUMMARY_TXT = _DATA / "cleaning_summary.txt"


# =========================
# 2. Helper Functions
# =========================

def find_csv_in_zip(zip_path: Path) -> str:
    """
    Find the first CSV file inside the ZIP archive.
    """
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        csv_files = [name for name in zip_ref.namelist() if name.lower().endswith(".csv")]

    if not csv_files:
        raise FileNotFoundError("No CSV file found inside the ZIP archive.")

    return csv_files[0]


def clean_text(text):
    """
    Clean text fields:
    - convert missing values to empty string
    - remove URLs
    - remove HTML tags
    - remove extra spaces
    """
    if pd.isna(text):
        return ""

    text = str(text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def standardize_category(text):
    """
    Standardize categorical text:
    - clean text
    - convert to lowercase
    """
    text = clean_text(text)
    if text == "":
        return "unknown"
    return text.lower()


# =========================
# 3. Load Dataset
# =========================

if not INPUT_ZIP.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT_ZIP}\n"
        "Please place 'WebMD Drug Reviews Dataset.zip' in the same folder as this script."
    )

csv_name = find_csv_in_zip(INPUT_ZIP)

df = pd.read_csv(
    INPUT_ZIP,
    compression="zip",
    low_memory=False
)

original_shape = df.shape


# =========================
# 4. Basic Column Cleaning
# =========================

# Remove leading/trailing spaces from column names
df.columns = df.columns.str.strip()

# Drop fully duplicated rows
duplicate_count = df.duplicated().sum()
df = df.drop_duplicates()


# =========================
# 5. Date Cleaning
# =========================

if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")


# =========================
# 6. Numeric Cleaning
# =========================

numeric_cols = [
    "EaseofUse",
    "Effectiveness",
    "Satisfaction",
    "UsefulCount"
]

existing_numeric_cols = [col for col in numeric_cols if col in df.columns]

for col in existing_numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Filter invalid rating values
rating_cols = ["EaseofUse", "Effectiveness", "Satisfaction"]
existing_rating_cols = [col for col in rating_cols if col in df.columns]

for col in existing_rating_cols:
    df = df[df[col].between(1, 5) | df[col].isna()]

# UsefulCount should not be negative
if "UsefulCount" in df.columns:
    df = df[(df["UsefulCount"] >= 0) | df["UsefulCount"].isna()]

# Fill numeric missing values with median
for col in existing_numeric_cols:
    median_value = df[col].median()
    df[col] = df[col].fillna(median_value)


# =========================
# 7. Text and Category Cleaning
# =========================

text_cols = ["Reviews", "Sides"]
category_cols = ["Drug", "Condition", "Sex", "Age"]

for col in text_cols:
    if col in df.columns:
        df[col] = df[col].apply(clean_text)

for col in category_cols:
    if col in df.columns:
        df[col] = df[col].apply(standardize_category)

# Replace empty side-effect text
if "Sides" in df.columns:
    df["Sides"] = df["Sides"].replace("", "no side effects reported")

# Remove empty or short reviews: require at least 10 words for meaningful NLP.
# Previous threshold (character length > 5) left single-word reviews like "satisfactory".
if "Reviews" in df.columns:
    df = df[df["Reviews"].apply(lambda x: len(str(x).split())) >= 10]


# =========================
# 8. Feature Engineering
# =========================

if "Reviews" in df.columns:
    df["review_length"] = df["Reviews"].str.len()
    df["word_count"] = df["Reviews"].apply(lambda x: len(str(x).split()))

if "Date" in df.columns:
    df["review_year"] = df["Date"].dt.year
    df["review_month"] = df["Date"].dt.month


# =========================
# 9. Final Quality Check
# =========================

final_shape = df.shape
missing_after_cleaning = df.isnull().sum()


# =========================
# 10. Save Cleaned Dataset
# =========================

df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")


# =========================
# 11. Save Cleaning Summary
# =========================

summary = f"""
WebMD Drug Reviews Dataset Cleaning Summary
==========================================

Input ZIP file:
{INPUT_ZIP}

CSV file detected inside ZIP:
{csv_name}

Original dataset shape:
Rows: {original_shape[0]}
Columns: {original_shape[1]}

Duplicate rows removed:
{duplicate_count}

Final cleaned dataset shape:
Rows: {final_shape[0]}
Columns: {final_shape[1]}

Output cleaned file:
{OUTPUT_CSV}

Missing values after cleaning:
{missing_after_cleaning.to_string()}

Cleaning steps completed:
1. Loaded CSV from ZIP file
2. Standardized column names
3. Removed duplicate rows
4. Converted Date column to datetime
5. Converted numeric rating columns to numeric type
6. Filtered invalid rating values outside 1-5
7. Removed invalid negative UsefulCount values
8. Filled numeric missing values using median
9. Cleaned text fields
10. Standardized categorical fields
11. Removed reviews with fewer than 10 words (raised from char-length > 5)
12. Added review_length and word_count features
13. Added review_year and review_month features
14. Saved cleaned CSV file
"""

SUMMARY_TXT.write_text(summary, encoding="utf-8")

print("Data cleaning completed successfully.")
print(f"Cleaned dataset saved to: {OUTPUT_CSV}")
print(f"Cleaning summary saved to: {SUMMARY_TXT}")
