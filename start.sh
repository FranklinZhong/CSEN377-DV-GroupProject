#!/usr/bin/env bash
# Render startup script for MedInsight backend.
# 1. If the database is missing, download it from DB_DOWNLOAD_URL (optional).
# 2. Start the FastAPI server.
set -e

DB_PATH="${DB_PATH:-/data/medinsight.db}"

if [ ! -f "$DB_PATH" ]; then
    if [ -n "$DB_DOWNLOAD_URL" ]; then
        echo "Database not found at $DB_PATH — downloading..."
        curl -L --retry 3 --progress-bar "$DB_DOWNLOAD_URL" -o "$DB_PATH"
        echo "Download complete: $(ls -lh "$DB_PATH" | awk '{print $5}')"
    else
        echo "WARNING: DB not found at $DB_PATH and DB_DOWNLOAD_URL is not set."
        echo "The API will start but return empty results until the DB is added."
    fi
else
    echo "Database ready: $(ls -lh "$DB_PATH" | awk '{print $5}')"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
