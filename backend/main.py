"""
MedInsight FastAPI Backend

启动：
  cd medinsight/
  uvicorn backend.main:app --reload --port 8000

API 文档：http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .api import search, drugs, trend, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup：初始化数据库表（幂等，DB 已存在则跳过）
    init_db()
    yield
    # shutdown：暂无需清理


app = FastAPI(
    title="MedInsight API",
    description="透明人体药物可视化平台后端 — CSEN 377 Spring 2026",
    version="0.2.0",
    lifespan=lifespan,
)

# Vue 3 dev server (port 5173) 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(search.router)
app.include_router(drugs.router)
app.include_router(trend.router)
app.include_router(health.router)
