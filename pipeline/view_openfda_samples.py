#!/usr/bin/env python3
"""
view_openfda_csv_samples.py

A lightweight CSV-only sampling/viewing tool for large cleaned openFDA drug label CSV files.

Typical use:
  python view_openfda_csv_samples.py --input data/processed/clean_label_master.csv --info
  python view_openfda_csv_samples.py --input data/processed/clean_label_master.csv --head 1000 --output data/processed/head_1000.csv
  python view_openfda_csv_samples.py --input data/processed/clean_label_master.csv --sample 1000 --output data/processed/random_sample_1000.csv
  python view_openfda_csv_samples.py --input data/processed/clean_label_master.csv --key-cols --sample 1000 --output data/processed/keycols_sample.csv
  python view_openfda_csv_samples.py --input data/processed/clean_label_master.csv --keyword aspirin --sample 1000 --output data/processed/aspirin_sample.csv
"""

import argparse
import os
import random
from pathlib import Path
from typing import List, Optional

import pandas as pd


DEFAULT_KEY_COLS = [
    "id",
    "set_id",
    "version",
    "effective_time",
    "brand_name",
    "generic_name",
    "manufacturer_name",
    "product_type",
    "route",
    "substance_name",
    "product_ndc",
    "has_boxed_warning",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="View or sample very large openFDA cleaned CSV files without parquet."
    )
    parser.add_argument("--input", required=True, help="Path to the large CSV file.")
    parser.add_argument("--output", help="Path to output small CSV file.")
    parser.add_argument("--info", action="store_true", help="Print file size, columns, and approximate row count.")
    parser.add_argument("--head", type=int, help="Export the first N rows.")
    parser.add_argument("--sample", type=int, help="Export a random sample of N rows using chunk reading.")
    parser.add_argument("--keyword", help="Filter rows containing this keyword in selected/search columns before sampling.")
    parser.add_argument(
        "--search-cols",
        nargs="+",
        help="Columns used for keyword search. If omitted, all columns are searched, which may be slower.",
    )
    parser.add_argument(
        "--key-cols",
        action="store_true",
        help="Only keep common important columns in the output if they exist.",
    )
    parser.add_argument(
        "--cols",
        nargs="+",
        help="Only keep these columns in the output if they exist.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=50000,
        help="Rows per chunk. Lower this if memory is still high. Default: 50000.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling. Default: 42.",
    )
    return parser.parse_args()


def get_columns(input_path: str) -> List[str]:
    return pd.read_csv(input_path, nrows=0).columns.tolist()


def existing_columns(all_cols: List[str], wanted_cols: Optional[List[str]]) -> Optional[List[str]]:
    if not wanted_cols:
        return None
    return [c for c in wanted_cols if c in all_cols]


def choose_output_columns(all_cols: List[str], args: argparse.Namespace) -> Optional[List[str]]:
    if args.cols:
        cols = existing_columns(all_cols, args.cols)
        if not cols:
            raise ValueError("None of the columns requested with --cols exist in the input CSV.")
        return cols
    if args.key_cols:
        cols = existing_columns(all_cols, DEFAULT_KEY_COLS)
        if not cols:
            raise ValueError("None of the default key columns exist in the input CSV.")
        return cols
    return None


def print_info(input_path: str, chunksize: int) -> None:
    path = Path(input_path)
    size_gb = path.stat().st_size / (1024 ** 3)
    cols = get_columns(input_path)

    print("\n========== CSV INFO ==========")
    print(f"File: {input_path}")
    print(f"File size: {size_gb:.2f} GB")
    print(f"Number of columns: {len(cols)}")
    print("\nColumns:")
    for i, col in enumerate(cols, 1):
        print(f"  {i:02d}. {col}")

    print("\nCounting rows by chunks...")
    total_rows = 0
    for chunk in pd.read_csv(input_path, chunksize=chunksize):
        total_rows += len(chunk)
    print(f"Approx / exact row count: {total_rows:,}")
    print("==============================\n")


def filter_keyword(chunk: pd.DataFrame, keyword: Optional[str], search_cols: Optional[List[str]]) -> pd.DataFrame:
    if not keyword:
        return chunk

    keyword_lower = keyword.lower()

    if search_cols:
        cols = [c for c in search_cols if c in chunk.columns]
    else:
        cols = list(chunk.columns)

    if not cols:
        return chunk.iloc[0:0]

    mask = pd.Series(False, index=chunk.index)
    for col in cols:
        mask = mask | chunk[col].astype(str).str.lower().str.contains(keyword_lower, na=False, regex=False)
    return chunk.loc[mask]


def export_head(input_path: str, output_path: str, n: int, usecols: Optional[List[str]], keyword: Optional[str], search_cols: Optional[List[str]], chunksize: int) -> None:
    rows = []
    collected = 0

    for chunk in pd.read_csv(input_path, chunksize=chunksize, usecols=usecols):
        chunk = filter_keyword(chunk, keyword, search_cols)
        if len(chunk) == 0:
            continue
        need = n - collected
        rows.append(chunk.head(need))
        collected += min(len(chunk), need)
        if collected >= n:
            break

    if not rows:
        print("No matching rows found. No output file created.")
        return

    out = pd.concat(rows, ignore_index=True)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Saved {len(out):,} rows to: {output_path}")


def reservoir_sample(input_path: str, output_path: str, n: int, usecols: Optional[List[str]], keyword: Optional[str], search_cols: Optional[List[str]], chunksize: int, seed: int) -> None:
    """Random sample from a huge CSV without loading it all into memory."""
    random.seed(seed)
    reservoir = []
    seen = 0

    for chunk in pd.read_csv(input_path, chunksize=chunksize, usecols=usecols):
        chunk = filter_keyword(chunk, keyword, search_cols)
        if len(chunk) == 0:
            continue

        for row in chunk.itertuples(index=False, name=None):
            seen += 1
            if len(reservoir) < n:
                reservoir.append(row)
            else:
                j = random.randint(1, seen)
                if j <= n:
                    reservoir[j - 1] = row

    if not reservoir:
        print("No matching rows found. No output file created.")
        return

    columns = usecols if usecols else get_columns(input_path)
    out = pd.DataFrame(reservoir, columns=columns)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Matched rows scanned: {seen:,}")
    print(f"Saved random sample of {len(out):,} rows to: {output_path}")


def main() -> None:
    args = parse_args()
    input_path = args.input

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not input_path.lower().endswith(".csv"):
        raise ValueError("This version only supports CSV input. Please provide a .csv file.")

    if args.info:
        print_info(input_path, args.chunksize)
        return

    if not args.output:
        raise ValueError("Please provide --output when exporting head or sample rows.")

    if not args.head and not args.sample:
        raise ValueError("Please choose one action: --info, --head N, or --sample N.")

    all_cols = get_columns(input_path)
    usecols = choose_output_columns(all_cols, args)

    if args.search_cols:
        missing = [c for c in args.search_cols if c not in all_cols]
        if missing:
            print(f"Warning: these --search-cols do not exist and will be ignored: {missing}")

    if args.head:
        export_head(
            input_path=input_path,
            output_path=args.output,
            n=args.head,
            usecols=usecols,
            keyword=args.keyword,
            search_cols=args.search_cols,
            chunksize=args.chunksize,
        )
    elif args.sample:
        reservoir_sample(
            input_path=input_path,
            output_path=args.output,
            n=args.sample,
            usecols=usecols,
            keyword=args.keyword,
            search_cols=args.search_cols,
            chunksize=args.chunksize,
            seed=args.seed,
        )


if __name__ == "__main__":
    main()
