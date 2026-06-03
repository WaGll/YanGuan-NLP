"""
FastAPI 应用入口

负责创建应用实例、注册中间件、挂载路由、管理生命周期。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    - 启动时：初始化数据库表
    - 关闭时：（暂无清理逻辑，预留扩展点）
    """
    await init_db()
    yield


# --- 创建应用实例 ---
app = FastAPI(
    title="GradCareer Comment Analysis API",
    description="高校毕业生就业评论分析系统 - 后端API",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS 中间件（开发阶段允许所有来源） ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 根路由 ---
@app.get("/")
async def root():
    """API 根路径，返回基本信息。"""
    return {
        "message": "GradCareer API",
        "docs": "/docs",
    }


# --- 健康检查 ---
@app.get("/api/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "healthy", "version": "0.1.0"}


# --- 注册各模块路由（后续阶段逐步接入） ---
# Phase 1: 仪表盘模块
from app.api.dashboard import router as dashboard_router  # noqa: E402

app.include_router(dashboard_router, prefix="/api")

# 预留路由注册点（后续阶段添加）：
# from app.api.sentiment import router as sentiment_router
# app.include_router(sentiment_router, prefix="/api")
# from app.api.keywords import router as keywords_router
# app.include_router(keywords_router, prefix="/api")
# from app.api.topics import router as topics_router
# app.include_router(topics_router, prefix="/api")
# from app.api.network import router as network_router
# app.include_router(network_router, prefix="/api")
# from app.api.upload import router as upload_router
# app.include_router(upload_router, prefix="/api")
