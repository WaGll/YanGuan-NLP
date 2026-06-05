"""测试情感分析 ML 模型得分 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ml_scores_empty(test_client: AsyncClient):
    """空数据库时 ML 分数端点返回空列表。"""
    response = await test_client.get("/api/sentiment/ml-scores")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0
