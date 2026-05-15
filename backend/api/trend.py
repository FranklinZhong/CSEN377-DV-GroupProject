from fastapi import APIRouter, Path, Depends, HTTPException
import sqlite3

from ..db import get_connection
from ..schemas.common import ok, err
from ..services.faers_service import get_trend_data
from ..services.drug_service import get_drug_by_id

router = APIRouter(prefix="/api/drugs", tags=["trend"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/{drug_id}/trend")
def drug_trend(
    drug_id: int = Path(..., gt=0),
    conn: sqlite3.Connection = Depends(_conn),
):
    """
    GET /api/drugs/{drug_id}/trend

    Returns Vis 2 timeline data:
    - timeline: quarterly report counts + brightness + CUSUM signal per (quarter, body_part)
    - signal_events: quarters where CUSUM triggered (used for ⚠ annotation)

    Data source: live FDA FAERS API (results cached for 7 days)
    """
    drug = get_drug_by_id(drug_id, conn)
    if not drug:
        raise HTTPException(status_code=404, detail=err("DRUG_NOT_FOUND",
            f"Drug #{drug_id} not found."))

    drug_name = drug.get("generic_name") or drug.get("name")
    result = get_trend_data(drug_name, drug_id, conn)

    warnings = []
    if not result.get("timeline"):
        warnings.append(
            "No FAERS data available for this drug. "
            "The drug may not appear frequently in adverse event reports."
        )
    if result.get("_warning"):
        warnings.append(result["_warning"])

    # Count signals to determine confidence level
    signals = [p for p in result.get("timeline", []) if p.get("signal_flag")]
    confidence = "high" if signals else "medium"

    return ok(
        {
            "drug_id":       drug_id,
            "drug_name":     drug_name,
            "timeline":      result.get("timeline", []),
            "signal_events": result.get("signal_events", []),
        },
        source="FDA FAERS API",
        confidence=confidence,
        report_count=sum(p.get("report_count", 0)
                         for p in result.get("timeline", [])),
        warnings=warnings,
    )
