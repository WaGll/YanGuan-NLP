"""LLM API 测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_llm_health(test_client: AsyncClient):
    """GET /api/llm/health 返回健康状态。"""
    response = await test_client.get("/api/llm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    health = data["data"]
    assert "available" in health
    assert "model" in health
    assert "base_url" in health


@pytest.mark.asyncio
async def test_llm_cache_stats(test_client: AsyncClient):
    """GET /api/llm/cache/stats 返回缓存统计。"""
    response = await test_client.get("/api/llm/cache/stats")
    assert response.status_code == 200
    data = response.json()
    stats = data["data"]
    assert "size" in stats
    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate" in stats


@pytest.mark.asyncio
async def test_clear_llm_cache(test_client: AsyncClient):
    """DELETE /api/llm/cache 清空缓存。"""
    response = await test_client.delete("/api/llm/cache")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "cleared" in data["data"]


@pytest.mark.asyncio
async def test_relabel_empty(test_client: AsyncClient):
    """POST /api/llm/relabel 空数据库返回空列表。"""
    response = await test_client.post(
        "/api/llm/relabel",
        json={"method": "lda"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["topics_refined"] == []
