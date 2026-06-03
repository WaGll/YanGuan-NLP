"""
API 依赖注入模块

提供路由处理函数中常用的 FastAPI Depends 依赖。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的 FastAPI 依赖。

    每个请求创建一个新会话，请求结束时自动提交或回滚。

    用法:
        from fastapi import Depends
        from app.api.deps import get_db

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(...))
            return result.scalars().all()
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
