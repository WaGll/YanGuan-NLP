"""测试主题×情感联合分析 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_topic_sentiment_default(test_client: AsyncClient):
    """测试默认参数获取主题-情感矩阵（空数据库）。"""
    response = await test_client.get("/api/topic-sentiment")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    # 空数据时也应返回合理结构
    assert "data" in data


@pytest.mark.asyncio
async def test_topic_sentiment_with_method(test_client: AsyncClient):
    """测试指定 method=lda 获取矩阵。"""
    response = await test_client.get("/api/topic-sentiment?method=lda")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
