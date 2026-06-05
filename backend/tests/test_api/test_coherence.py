"""Coherence API 测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compare_coherence_empty(test_client: AsyncClient):
    """GET /api/coherence/compare 空数据库返回空对比。"""
    response = await test_client.get("/api/coherence/compare")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    compare = data["data"]
    assert "methods" in compare
    assert "winner" in compare


@pytest.mark.asyncio
async def test_per_comment_coherence_empty(test_client: AsyncClient):
    """GET /api/coherence/per-comment 空数据库返回空列表。"""
    response = await test_client.get("/api/coherence/per-comment")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_per_comment_coherence_pagination(test_client: AsyncClient):
    """GET /api/coherence/per-comment 分页参数验证。"""
    response = await test_client.get(
        "/api/coherence/per-comment",
        params={"page": 1, "page_size": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 10


@pytest.mark.asyncio
async def test_mixed_topics_empty(test_client: AsyncClient):
    """GET /api/coherence/mixed-topics 空数据库返回空列表。"""
    response = await test_client.get("/api/coherence/mixed-topics")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"] == []


@pytest.mark.asyncio
async def test_coherence_summary_empty(test_client: AsyncClient):
    """GET /api/coherence/summary 空数据库返回 null 方法指标。"""
    response = await test_client.get("/api/coherence/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    summary = data["data"]
    assert summary["lda"] is None
    assert summary["bertopic"] is None
    assert summary["mixed_topic_count"] == 0
