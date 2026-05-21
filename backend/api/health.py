from fastapi import APIRouter
from datetime import datetime

from ..db import db_session
from ..schemas.common import ok

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check():
    """
    GET /api/health
    Returns service status and data version for the frontend summary bar.
    """
    try:
        with db_session() as conn:
            drug_count = conn.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
            row = conn.execute(
                "SELECT data_version, updated_at FROM drugs ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        data_version = row["data_version"] if row else "unknown"
        last_updated = row["updated_at"] if row else "unknown"
        db_ok = True
    except Exception:
        drug_count = 0
        data_version = "unknown"
        last_updated = "unknown"
        db_ok = False

    return ok(
        {
            "status":       "ok" if db_ok else "degraded",
            "drug_count":   drug_count,
            "data_version": data_version,
            "last_updated": last_updated,
            "server_time":  datetime.utcnow().isoformat(),
        },
        source="SQLite",
        confidence="high",
    )
