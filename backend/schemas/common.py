"""
Unified API response envelope used by every endpoint.

All endpoints return:
  { success, data, meta, warnings }   on success
  { success, error, suggestions }     on failure
"""

from typing import Any
from pydantic import BaseModel


class Meta(BaseModel):
    source: str = "unknown"
    data_version: str = "2026Q1"
    confidence: str = "medium"      # high | medium | low | insufficient
    report_count: int | None = None


class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    meta: Meta = Meta()
    warnings: list[str] = []


class ApiError(BaseModel):
    success: bool = False
    error: dict[str, str] = {}
    suggestions: list[str] = []


def ok(data: Any, *, source: str = "unknown", confidence: str = "medium",
       report_count: int | None = None, data_version: str = "2026Q1",
       warnings: list[str] | None = None) -> dict:
    return ApiResponse(
        data=data,
        meta=Meta(source=source, confidence=confidence,
                  report_count=report_count, data_version=data_version),
        warnings=warnings or [],
    ).model_dump()


def err(code: str, message: str, suggestions: list[str] | None = None) -> dict:
    return ApiError(
        error={"code": code, "message": message},
        suggestions=suggestions or [],
    ).model_dump()
