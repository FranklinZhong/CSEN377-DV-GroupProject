#!/usr/bin/env bash
# Downloads the 13 OpenFDA drug label zip files from the official FDA bulk dataset.
# Target: data/raw/ (relative to this script's directory)
# Usage:  bash download_openfda.sh
# Resume: re-run the same command; curl -C - skips already-complete files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Canonical raw destination: medinsight/data/processed/OpenFDA/data/raw/
OPENFDA_DIR="$(dirname "$SCRIPT_DIR")/data/processed/OpenFDA/data"
RAW_DIR="$OPENFDA_DIR/raw"
mkdir -p "$RAW_DIR"

BASE_URL="https://download.open.fda.gov/drug/label"
TOTAL=13

echo "Downloading $TOTAL OpenFDA drug label zip files → $RAW_DIR"
echo "Total estimated size: ~1.82 GB"
echo "Tip: if interrupted, re-run this script — curl will resume incomplete files."
echo ""

for i in $(seq -f "%04g" 1 $TOTAL); do
    FILE="drug-label-${i}-of-$(printf '%04d' $TOTAL).json.zip"
    URL="$BASE_URL/$FILE"
    DEST="$RAW_DIR/$FILE"

    if [[ -f "$DEST" ]]; then
        echo "[$i/$TOTAL] Already complete: $FILE — skipping"
        continue
    fi

    echo "[$i/$TOTAL] Downloading $FILE ..."
    curl -C - --retry 3 --retry-delay 5 \
         --progress-bar \
         -o "$DEST" \
         "$URL"
    echo "[$i/$TOTAL] Done: $FILE"
done

echo ""
echo "All $TOTAL files downloaded to $RAW_DIR"
echo ""
echo "Next step — run the streaming pipeline:"
echo "  python pipeline/clean_openfda_streaming.py \\"
echo "      --input-dir data/processed/OpenFDA/data/raw \\"
echo "      --output-dir data/processed/OpenFDA/data/processed \\"
echo "      --report data/processed/reports/openfda_cleaning_report.md"
