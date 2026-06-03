"""
pytest 公共 Fixtures

提供测试数据库引擎、异步会话和 HTTP 测试客户端。
所有测试使用内存 SQLite，互相隔离。
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """为整个测试会话创建事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """创建内存 SQLite 测试引擎，自动建表。

    每个测试函数获得独立的内存数据库实例。
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    """创建测试会话工厂。"""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def test_db(
    test_session_factory,
) -> AsyncGenerator[AsyncSession, None]:
    """提供测试数据库会话，测试结束时自动回滚。"""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(
    test_db: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """提供 FastAPI 异步测试客户端。

    覆盖 get_db 依赖，使所有 API 请求使用测试数据库会话。
    """
    from app.api.deps import get_db
    from app.main import app

    # 覆盖依赖注入，使路由使用测试数据库
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
