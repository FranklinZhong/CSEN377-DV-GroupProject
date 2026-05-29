"""
MedInsight FastAPI Backend

Start:
  cd medinsight/
  uvicorn backend.main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .api import search, drugs, trend, health, corpus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialize DB tables (idempotent — skipped if DB already exists)
    init_db()
    yield
    # shutdown: nothing to clean up


app = FastAPI(
    title="MedInsight API",
    description="Transparent human body drug visualization platform backend — CSEN 377 Spring 2026",
    version="0.2.0",
    lifespan=lifespan,
)

_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allowed_origins = os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(search.router)
app.include_router(drugs.router)
app.include_router(trend.router)
app.include_router(health.router)
app.include_router(corpus.router)
