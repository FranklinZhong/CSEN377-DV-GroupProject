#!/usr/bin/env bash
# Render startup script for MedInsight backend.
# 1. If the database is missing, download it from DB_DOWNLOAD_URL (optional).
# 2. Start the FastAPI server.
set -e

DB_PATH="${DB_PATH:-/tmp/medinsight.db}"

if [ ! -f "$DB_PATH" ]; then
    if [ -n "$DB_DOWNLOAD_URL" ]; then
        echo "Database not found at $DB_PATH — downloading..."
        pip install gdown -q
        # --fuzzy accepts any Google Drive URL format (sharing link, uc?export=, /file/d/)
        if gdown --fuzzy "$DB_DOWNLOAD_URL" -O "$DB_PATH"; then
            echo "Download complete: $(ls -lh "$DB_PATH" | awk '{print $5}')"
        else
            echo "WARNING: DB download failed. API will start but return empty results."
            rm -f "$DB_PATH"
        fi
    else
        echo "WARNING: DB_DOWNLOAD_URL not set. API will start but return empty results."
    fi
else
    echo "Database ready: $(ls -lh "$DB_PATH" | awk '{print $5}')"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
