"""测试语义网络 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_network_default(test_client: AsyncClient):
    """测试默认参数获取网络图数据（空数据库触发构建）。"""
    response = await test_client.get("/api/network")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    # 网络数据应包含 nodes 和 edges
    assert "nodes" in data["data"]
    assert "edges" in data["data"]


@pytest.mark.asyncio
async def test_network_with_params(test_client: AsyncClient):
    """测试自定义 min_edge_weight 和 max_nodes。"""
    response = await test_client.get("/api/network?min_edge_weight=3&max_nodes=50")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_network_param_validation(test_client: AsyncClient):
    """测试参数边界验证。"""
    # max_nodes 至少为 2
    response = await test_client.get("/api/network?max_nodes=1")
    assert response.status_code == 422

    # max_nodes 最多为 1000
    response = await test_client.get("/api/network?max_nodes=1001")
    assert response.status_code == 422

    # min_edge_weight 至少为 1
    response = await test_client.get("/api/network?min_edge_weight=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_network_metrics_default(test_client: AsyncClient):
    """测试网络指标端点默认参数（空数据库）。"""
    response = await test_client.get("/api/network/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    metrics = data["data"]
    assert "cooccurrence_matrix" in metrics
    assert "top_central_nodes" in metrics
    assert "statistics" in metrics
    assert "keywords" in metrics["cooccurrence_matrix"]
    assert "matrix" in metrics["cooccurrence_matrix"]


@pytest.mark.asyncio
async def test_network_metrics_with_top_n(test_client: AsyncClient):
    """测试网络指标端点自定义 top_n。"""
    response = await test_client.get("/api/network/metrics?top_n=10")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_network_metrics_param_validation(test_client: AsyncClient):
    """测试网络指标参数验证。"""
    # top_n < 5
    response = await test_client.get("/api/network/metrics?top_n=3")
    assert response.status_code == 422
    # top_n > 100
    response = await test_client.get("/api/network/metrics?top_n=200")
    assert response.status_code == 422
