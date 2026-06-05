"""聚合 API 测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_aggregation_config(test_client: AsyncClient):
    """GET /api/aggregation/config 返回当前配置。"""
    response = await test_client.get("/api/aggregation/config")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    cfg = data["data"]
    assert "enabled" in cfg
    assert "window_minutes" in cfg
    assert "min_comments" in cfg


@pytest.mark.asyncio
async def test_get_aggregation_status_empty(test_client: AsyncClient):
    """GET /api/aggregation/status 空数据库返回零值。"""
    response = await test_client.get("/api/aggregation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    status = data["data"]
    assert status["total_groups"] == 0
    assert status["coverage_pct"] == 0.0


@pytest.mark.asyncio
async def test_update_aggregation_config(test_client: AsyncClient):
    """PUT /api/aggregation/config 更新运行时配置。"""
    response = await test_client.put(
        "/api/aggregation/config",
        json={"window_minutes": 60, "min_comments": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["window_minutes"] == 60
    assert data["data"]["min_comments"] == 3


@pytest.mark.asyncio
async def test_update_aggregation_config_partial(test_client: AsyncClient):
    """PUT /api/aggregation/config 部分更新。"""
    response = await test_client.put(
        "/api/aggregation/config",
        json={"enabled": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["enabled"] is False


@pytest.mark.asyncio
async def test_run_aggregation_empty(test_client: AsyncClient):
    """POST /api/aggregation/run 空数据库返回 0 组。"""
    response = await test_client.post(
        "/api/aggregation/run",
        params={"window_minutes": 60, "min_comments": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["groups_created"] == 0
