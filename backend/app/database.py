"""
数据库模块

提供异步 SQLAlchemy 引擎、会话工厂、依赖注入函数及数据库初始化逻辑。
使用 SQLite + aiosqlite 作为默认后端，开启 WAL 模式以支持并发读写。
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# --- 异步引擎 ---
engine = create_async_engine(
    str(settings.database_url),
    echo=False,
    future=True,
)


# 为 SQLite 启用 WAL 模式，提升并发性能
@event.listens_for(engine.sync_engine, "connect")  # type: ignore[misc]
def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """在每次新连接时设置 SQLite PRAGMA。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


# --- 会话工厂 ---
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- 声明式基类（从 models.base 导入，确保所有模型共用同一个 Base） ---
from app.models.base import Base  # noqa: E402


# --- 依赖注入 ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取一个异步数据库会话，请求结束时自动关闭。

    用法:
        from fastapi import Depends
        from app.database import get_db

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# --- 初始化 ---
async def init_db() -> None:
    """创建所有数据库表。

    应在应用启动时调用一次。
    """
    # 确保所有模型已导入，以便 DeclarativeBase 发现它们
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
