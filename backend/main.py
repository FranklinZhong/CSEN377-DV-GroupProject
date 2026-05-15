"""
MedInsight FastAPI Backend

Start:
  uvicorn backend.main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .api import search, drugs, trend, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="MedInsight API",
    description="MedInsight drug visualization platform backend — CSEN 377 Spring 2026",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(drugs.router)
app.include_router(trend.router)
app.include_router(health.router)
