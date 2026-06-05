"""
FastAPI 应用入口

负责创建应用实例、注册中间件、挂载路由、管理生命周期。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    - 启动时：初始化数据库表，加载 NLP 资源
    - 关闭时：（暂无清理逻辑，预留扩展点）
    """
    # 初始化数据库表
    await init_db()

    # 加载 NLP 资源（jieba 词典、停用词、同义词表）
    from app.utils.resources import NLPResources

    data_dir = settings.data_dir
    try:
        NLPResources.get_instance().load(data_dir)
        logger.info("NLPResources 加载完成")
    except Exception as e:
        logger.warning("NLPResources 加载失败（部分 NLP 功能可能不可用）: %s", e)

    yield


# --- 创建应用实例 ---
app = FastAPI(
    title="YanGuan-NLP API",
    description="研观 — 考研评论多维度 NLP 分析平台",
    version="1.1.0",
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
        "message": "YanGuan-NLP API",
        "docs": "/docs",
    }


# --- 健康检查 ---
@app.get("/api/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "healthy", "version": "1.1.0"}


# =============================================================================
# 注册各模块路由
# =============================================================================

# 仪表盘
from app.api.dashboard import router as dashboard_router  # noqa: E402

app.include_router(dashboard_router, prefix="/api")

# 情感分析
from app.api.sentiment import router as sentiment_router  # noqa: E402

app.include_router(sentiment_router, prefix="/api")

# 关键词
from app.api.keywords import router as keywords_router  # noqa: E402

app.include_router(keywords_router, prefix="/api")

# 主题分析
from app.api.topics import router as topics_router  # noqa: E402

app.include_router(topics_router, prefix="/api")

# 主题×情感联合分析
from app.api.topic_sentiment import router as topic_sentiment_router  # noqa: E402

app.include_router(topic_sentiment_router, prefix="/api")

# 趋势分析
from app.api.trends import router as trends_router  # noqa: E402

app.include_router(trends_router, prefix="/api")

# 共现网络
from app.api.network import router as network_router  # noqa: E402

app.include_router(network_router, prefix="/api")

# 实时预测
from app.api.predict import router as predict_router  # noqa: E402

app.include_router(predict_router, prefix="/api")

# 表情分析
from app.api.emotes import router as emotes_router  # noqa: E402

app.include_router(emotes_router, prefix="/api")

# 短文本聚合管理
from app.api.aggregation import router as aggregation_router  # noqa: E402

app.include_router(aggregation_router, prefix="/api")

# 双轨 Coherence 评估
from app.api.coherence import router as coherence_router  # noqa: E402

app.include_router(coherence_router, prefix="/api")

# LLM 标签管理
from app.api.llm import router as llm_router  # noqa: E402

app.include_router(llm_router, prefix="/api")
