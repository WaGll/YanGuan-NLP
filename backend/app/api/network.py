"""
语义网络 API 路由

提供关键词共现网络图的节点和边数据，供前端力导向图/网络图渲染。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.network import NetworkEdge, NetworkNode
from app.schemas.common import APIResponse
from app.services.network import NetworkService

router = APIRouter(tags=["语义网络"])


@router.get("/network")
async def get_network(
    min_edge_weight: int = Query(
        2, ge=1, description="最小边权重阈值，过滤低频共现边"
    ),
    max_nodes: int = Query(
        200, ge=2, le=1000, description="最大节点数"
    ),
    db: AsyncSession = Depends(get_db),
):
    """获取关键词共现网络图数据。

    - **min_edge_weight**: 最小边权重，仅返回共现次数 >= 此值的边
    - **max_nodes**: 最大节点数，超出时按度中心性截断
    - 返回 nodes（含 id/name/size/category/中心性）和 edges（含 source/target/weight）
    """
    # 优先从数据库读取已缓存的网络数据
    node_count_result = await db.execute(
        select(func.count(NetworkNode.id))
    )
    node_count = node_count_result.scalar() or 0

    if node_count == 0:
        # 数据库中无网络数据，触发构建
        service = NetworkService(db)
        graph_data = await service.build_cooccurrence_graph(
            top_k=max_nodes, window=2
        )
    else:
        # 从数据库读取
        node_result = await db.execute(
            select(NetworkNode).order_by(
                NetworkNode.degree_centrality.desc().nullslast()
            ).limit(max_nodes)
        )
        nodes = node_result.scalars().all()

        node_names = [n.word for n in nodes]
        edge_result = await db.execute(
            select(NetworkEdge).where(
                NetworkEdge.source_word.in_(node_names),
                NetworkEdge.target_word.in_(node_names),
            )
        )
        edges = edge_result.scalars().all()

        # 过滤边权重
        graph_data = {
            "nodes": [
                {
                    "id": n.word,
                    "name": n.word,
                    "symbolSize": max(4, min(50, n.frequency // 10)),
                    "category": n.community_id or 0,
                    "frequency": n.frequency,
                    "degree_centrality": round(n.degree_centrality, 4) if n.degree_centrality else 0,
                    "betweenness_centrality": round(n.betweenness_centrality, 4) if n.betweenness_centrality else 0,
                    "eigenvector_centrality": round(n.eigenvector_centrality, 4) if n.eigenvector_centrality else 0,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source_word,
                    "target": e.target_word,
                    "weight": e.weight,
                }
                for e in edges
                if e.weight >= min_edge_weight
            ],
        }

    return APIResponse(data=graph_data)
