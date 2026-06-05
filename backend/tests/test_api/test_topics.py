"""测试主题分析 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_topics_default(test_client: AsyncClient):
    """测试默认参数获取主题列表（空数据库）。"""
    response = await test_client.get("/api/topics")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_topics_with_method_lda(test_client: AsyncClient):
    """测试指定 method=lda 获取主题列表。"""
    response = await test_client.get("/api/topics?method=lda")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
