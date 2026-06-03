"""测试仪表盘 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """测试健康检查端点。"""
    response = await test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(test_client: AsyncClient):
    """测试根路径。"""
    response = await test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_dashboard_empty(test_client: AsyncClient):
    """测试空数据库的仪表盘返回。"""
    response = await test_client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["total_comments"] == 0
    assert data["data"]["unique_users"] == 0


@pytest.mark.asyncio
async def test_sentiment_empty(test_client: AsyncClient):
    """测试空数据库的情感分析返回。"""
    response = await test_client.get("/api/sentiment")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"]["bins"], list)


@pytest.mark.asyncio
async def test_keywords_empty(test_client: AsyncClient):
    """测试空数据库的关键词返回。"""
    response = await test_client.get("/api/keywords")
    assert response.status_code == 200
