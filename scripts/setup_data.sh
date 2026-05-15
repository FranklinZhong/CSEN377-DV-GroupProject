#!/usr/bin/env bash
# setup_data.sh — Download raw datasets and build the SQLite database
#
# Requirements:
#   - kaggle CLI configured with API key
#     See: https://www.kaggle.com/docs/api
#   - Python 3.10+ with dependencies installed (pip install -r requirements.txt)
#   - curl (for OpenFDA download)
#
# Usage:
#   bash scripts/setup_data.sh            # full setup (recommended for first run)
#   bash scripts/setup_data.sh --skip-dl  # skip downloads, only run pipeline
#
# Estimated time: 30-60 minutes depending on connection speed
# Estimated disk: ~9 GB (raw) + ~200 MB (medinsight.db)

set -e

SKIP_DL=false
for arg in "$@"; do
  [[ "$arg" == "--skip-dl" ]] && SKIP_DL=true
done

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== MedInsight Data Setup ==="
echo "Working directory: $ROOT_DIR"
echo ""

# ── Directory structure ────────────────────────────────────────────────────────
mkdir -p data/raw/faers \
         data/raw/webmd \
         data/processed/FAERS \
         data/processed/WebMDReview \
         data/processed/OpenFDA/data/raw \
         data/processed/OpenFDA/data/processed \
         data/processed/reports

if [ "$SKIP_DL" = false ]; then
  # ── 1. FAERS (Kaggle) ─────────────────────────────────────────────────────
  echo "[1/3] Downloading FAERS drug event signals from Kaggle..."
  kaggle datasets download -d anurmi/faers-drug-event-signals \
    -p data/raw/faers --unzip
  echo "      FAERS download complete."

  # ── 2. WebMD Reviews (Kaggle) ─────────────────────────────────────────────
  echo "[2/3] Downloading WebMD drug reviews from Kaggle..."
  kaggle datasets download -d rohanharode07/webmd-drug-reviews-dataset \
    -p data/raw/webmd --unzip
  echo "      WebMD download complete."

  # ── 3. OpenFDA Drug Labels (~1.82 GB, 13 zip files) ───────────────────────
  echo "[3/3] Downloading OpenFDA drug label data (supports resume)..."
  bash pipeline/download_openfda.sh
  echo "      OpenFDA download complete."
else
  echo "[INFO] Skipping downloads (--skip-dl)"
fi

# ── 4. Run full pipeline → generates data/processed/medinsight.db ─────────────
echo ""
echo "[4/4] Running data pipeline (this may take 20-40 minutes)..."
python pipeline/run_pipeline.py

echo ""
echo "=============================================="
echo " Setup complete!"
echo " Database: data/processed/medinsight.db"
echo ""
echo " To start the app:"
echo "   Terminal 1: uvicorn backend.main:app --reload --port 8000"
echo "   Terminal 2: cd frontend && npm install && npx vite --port 5173"
echo "   Open: http://localhost:5173"
echo "=============================================="
