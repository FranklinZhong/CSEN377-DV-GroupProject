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
        # Extract file ID from /file/d/ID/ or ?id=ID formats.
        FILE_ID=$(echo "$DB_DOWNLOAD_URL" | grep -oP '(?<=/file/d/)[^/?]+' || true)
        if [ -z "$FILE_ID" ]; then
            FILE_ID=$(echo "$DB_DOWNLOAD_URL" | grep -oP '(?<=id=)[^&]+' || true)
        fi
        if [ -z "$FILE_ID" ]; then
            echo "WARNING: Could not extract file ID from DB_DOWNLOAD_URL."
            echo "The API will start but return empty results."
        elif gdown "$FILE_ID" -O "$DB_PATH"; then
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
