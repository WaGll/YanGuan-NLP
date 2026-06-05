"""测试趋势分析 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trends_default(test_client: AsyncClient):
    """测试默认参数获取趋势数据（空数据库）。"""
    response = await test_client.get("/api/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data


@pytest.mark.asyncio
async def test_trends_with_params(test_client: AsyncClient):
    """测试指定 series_type 和 granularity。"""
    response = await test_client.get("/api/trends?series_type=sentiment&granularity=month")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_trends_different_granularity(test_client: AsyncClient):
    """测试不同时间粒度。"""
    for granularity in ["day", "week", "month", "year"]:
        response = await test_client.get(f"/api/trends?granularity={granularity}")
        assert response.status_code == 200
