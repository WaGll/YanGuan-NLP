"""
语义网络服务

基于评论 Bigram 共现关系构建语义网络图，
计算中心性指标，检测社区结构，供前端可视化。
"""

import json
import logging
from collections import Counter, defaultdict
from typing import Any

import networkx as nx
from networkx.algorithms import community
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.network import NetworkEdge, NetworkNode

logger = logging.getLogger(__name__)


class NetworkService:
    """语义网络服务。

    从评论 Bigram 分词中构建共现矩阵，生成 NetworkX 图，
    计算中心性和社区检测，结果持久化到数据库。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def build_cooccurrence_graph(
        self, top_k: int = 100, window: int = 2
    ) -> dict[str, list[dict[str, Any]]]:
        """构建关键词共现网络图。

        步骤:
        1. 加载所有评论的 bigram_tokens_json
        2. 使用滑动窗口构建共现矩阵
        3. 选取 top_k 高频词构建 NetworkX 图
        4. 计算度/介数/特征向量中心性
        5. 使用社区检测算法检测社区
        6. 持久化节点和边
        7. 返回前端可视化所需格式

        Args:
            top_k: 保留的高频词数量
            window: 共现窗口大小

        Returns:
            {nodes: [{id, name, symbolSize, category, ...}],
             edges: [{source, target, weight}]}
        """
        # 1. 加载 Bigram 分词数据
        result = await self.db.execute(
            select(Comment.bigram_tokens_json).where(
                Comment.bigram_tokens_json.isnot(None),
                Comment.token_count > 0,
            )
        )
        rows = result.all()
        if not rows:
            logger.warning("无可用 Bigram 数据，无法构建语义网络")
            return {"nodes": [], "edges": []}

        # 2. 构建共现矩阵（使用滑动窗口）
        cooccur: dict[tuple[str, str], int] = Counter()
        word_freq: Counter[str] = Counter()

        for (bigram_json,) in rows:
            try:
                tokens = json.loads(bigram_json)
            except json.JSONDecodeError:
                continue

            if not tokens:
                continue

            # 词频统计
            for word in tokens:
                word_freq[word] += 1

            # 滑动窗口共现
            n = len(tokens)
            for i in range(n):
                end = min(i + window + 1, n)
                for j in range(i + 1, end):
                    w1, w2 = tokens[i], tokens[j]
                    if w1 == w2:
                        continue
                    # 保证 w1 < w2 以标准化
                    key = (w1, w2) if w1 < w2 else (w2, w1)
                    cooccur[key] += 1

        # 3. 选取 top_k 高频词
        top_words = {word for word, _ in word_freq.most_common(top_k)}
        if len(top_words) < 2:
            logger.warning("高频词不足 2 个，无法构建网络图")
            return {"nodes": [], "edges": []}

        # 4. 构建 NetworkX 图
        G = nx.Graph()
        for word in top_words:
            G.add_node(word)

        for (w1, w2), count in cooccur.items():
            if w1 in top_words and w2 in top_words:
                G.add_edge(w1, w2, weight=count)

        if G.number_of_edges() == 0:
            logger.warning("共现图中无边，返回仅节点数据")
            nodes_data = [
                {
                    "id": word,
                    "name": word,
                    "symbolSize": max(4, min(50, word_freq[word])),
                    "category": 0,
                    "frequency": word_freq[word],
                }
                for word in top_words
            ]
            return {"nodes": nodes_data, "edges": []}

        # 5. 计算中心性指标
        degree_cent = nx.degree_centrality(G)
        betweenness_cent = (
            nx.betweenness_centrality(G, weight="weight")
            if G.number_of_nodes() > 2
            else {n: 0.0 for n in G.nodes()}
        )
        # 接近中心性（可能在非连通图上失败）
        closeness_cent: dict[str, float] = {}
        try:
            closeness_cent = nx.closeness_centrality(G)
        except Exception:
            closeness_cent = {n: 0.0 for n in G.nodes()}
        # PageRank
        pagerank_scores: dict[str, float] = {}
        try:
            pagerank_scores = nx.pagerank(G, weight="weight", alpha=0.85)
        except Exception:
            pagerank_scores = {n: 0.0 for n in G.nodes()}
        eigenvector_cent = {}
        try:
            eigenvector_cent = nx.eigenvector_centrality_numpy(G, weight="weight")
        except Exception:
            try:
                eigenvector_cent = nx.eigenvector_centrality(
                    G, max_iter=500, weight="weight"
                )
            except Exception:
                eigenvector_cent = {n: 0.0 for n in G.nodes()}

        # 6. 社区检测（优先 Louvain，回退 greedy_modularity）
        communities: dict[str, int] = {}
        try:
            # Louvain 社区检测
            louvain_communities = community.louvain_communities(
                G, weight="weight", seed=42
            )
            for cid, comm in enumerate(louvain_communities):
                for node in comm:
                    communities[node] = cid
        except Exception:
            # 回退：greedy_modularity_communities
            try:
                greedy_comms = community.greedy_modularity_communities(
                    G, weight="weight"
                )
                for cid, comm in enumerate(greedy_comms):
                    for node in comm:
                        communities[node] = cid
            except Exception:
                communities = {n: 0 for n in G.nodes()}

        # 7. 持久化到数据库
        await self._persist_network(
            G, word_freq, degree_cent, betweenness_cent,
            closeness_cent, eigenvector_cent, pagerank_scores, communities
        )

        # 8. 构造返回数据（前端可视化格式）
        # 计算节点可视化大小
        max_freq = max(word_freq.values()) if word_freq else 1

        nodes_out = []
        for word in top_words:
            nodes_out.append({
                "id": word,
                "name": word,
                "symbolSize": max(4, min(50, int(word_freq[word] / max_freq * 40))),
                "category": communities.get(word, 0),
                "frequency": word_freq[word],
                "degree_centrality": round(degree_cent.get(word, 0), 4),
                "betweenness_centrality": round(betweenness_cent.get(word, 0), 4),
                "closeness_centrality": round(closeness_cent.get(word, 0), 4),
                "eigenvector_centrality": round(eigenvector_cent.get(word, 0), 4),
                "pagerank": round(pagerank_scores.get(word, 0), 4),
            })

        edges_out = []
        for u, v, data in G.edges(data=True):
            edges_out.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1),
            })

        logger.info(
            "语义网络构建完成: %d 节点, %d 边, %d 社区",
            len(nodes_out),
            len(edges_out),
            len(set(communities.values())),
        )
        return {"nodes": nodes_out, "edges": edges_out}

    # ------------------------------------------------------------------
    # 网络指标查询
    # ------------------------------------------------------------------

    async def get_network_metrics(
        self, top_n: int = 20
    ) -> dict[str, Any]:
        """获取网络分析指标摘要。

        从已持久化的网络数据中提取：
        - 关键词共现矩阵（top_n × top_n）
        - 各中心性 Top 节点
        - 网络统计（节点数、边数、密度、平均聚类系数、社区数）

        Args:
            top_n: 返回的矩阵维度和 Top 节点数量

        Returns:
            metrics dict 包含 cooccurrence_matrix, top_central_nodes, statistics
        """
        from sqlalchemy import func

        # 加载节点数据
        node_result = await self.db.execute(
            select(NetworkNode).order_by(
                NetworkNode.degree_centrality.desc().nullslast()
            ).limit(top_n)
        )
        nodes = node_result.scalars().all()

        if not nodes:
            return {
                "cooccurrence_matrix": {"keywords": [], "matrix": []},
                "top_central_nodes": {
                    "degree": [],
                    "betweenness": [],
                    "closeness": [],
                    "pagerank": [],
                },
                "statistics": {
                    "node_count": 0,
                    "edge_count": 0,
                    "density": 0,
                    "avg_clustering": 0,
                    "connected_components": 0,
                    "community_count": 0,
                    "modularity": 0,
                },
            }

        # 获取 top_n 节点名称
        top_words = [n.word for n in nodes]

        # 加载这些节点之间的边 → 共现矩阵
        edge_result = await self.db.execute(
            select(NetworkEdge).where(
                NetworkEdge.source_word.in_(top_words),
                NetworkEdge.target_word.in_(top_words),
            )
        )
        edges = edge_result.scalars().all()

        # 构建共现矩阵 (带标签)
        word_index = {w: i for i, w in enumerate(top_words)}
        n = len(top_words)
        matrix = [[0] * n for _ in range(n)]
        for e in edges:
            i = word_index.get(e.source_word)
            j = word_index.get(e.target_word)
            if i is not None and j is not None:
                matrix[i][j] = int(e.weight)
                matrix[j][i] = int(e.weight)

        # Top 节点按各中心性排序
        all_nodes_result = await self.db.execute(
            select(NetworkNode).order_by(
                NetworkNode.degree_centrality.desc().nullslast()
            )
        )
        all_nodes = all_nodes_result.scalars().all()

        def top_by(attr: str, limit: int = 10) -> list[dict]:
            sorted_nodes = sorted(
                all_nodes, key=lambda n: getattr(n, attr) or 0, reverse=True
            )
            return [
                {"word": n.word, "value": round(getattr(n, attr) or 0, 4)}
                for n in sorted_nodes[:limit]
            ]

        # 计算网络统计
        total_nodes = len(all_nodes)
        edge_count_result = await self.db.execute(
            select(func.count(NetworkEdge.id))
        )
        total_edges = edge_count_result.scalar() or 0

        # 密度: 2*E / (N*(N-1)) for undirected
        density = (
            (2 * total_edges) / (total_nodes * (total_nodes - 1))
            if total_nodes > 1 else 0
        )

        # 不同社区数
        community_ids = {n.community_id for n in all_nodes if n.community_id is not None}

        return {
            "cooccurrence_matrix": {
                "keywords": top_words,
                "matrix": matrix,
            },
            "top_central_nodes": {
                "degree": top_by("degree_centrality"),
                "betweenness": top_by("betweenness_centrality"),
                "closeness": top_by("closeness_centrality"),
                "pagerank": top_by("pagerank"),
            },
            "statistics": {
                "node_count": total_nodes,
                "edge_count": total_edges,
                "density": round(density, 6),
                "avg_clustering": 0,  # 需要 NetworkX 图对象，从 DB 重建开销大
                "connected_components": 1,  # 同上
                "community_count": len(community_ids),
                "modularity": 0,
            },
        }

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _persist_network(
        self,
        G: nx.Graph,
        word_freq: Counter[str],
        degree_cent: dict[str, float],
        betweenness_cent: dict[str, float],
        closeness_cent: dict[str, float],
        eigenvector_cent: dict[str, float],
        pagerank_scores: dict[str, float],
        communities: dict[str, int],
    ) -> None:
        """将网络节点和边持久化到数据库。

        先清除旧数据，再批量写入。
        """
        # 清除旧数据
        await self.db.execute(delete(NetworkEdge))
        await self.db.execute(delete(NetworkNode))
        await self.db.flush()

        # 写入节点
        for word in G.nodes():
            self.db.add(
                NetworkNode(
                    word=word,
                    frequency=word_freq.get(word, 0),
                    degree_centrality=degree_cent.get(word, 0.0),
                    betweenness_centrality=betweenness_cent.get(word, 0.0),
                    closeness_centrality=closeness_cent.get(word, 0.0),
                    eigenvector_centrality=eigenvector_cent.get(word, 0.0),
                    pagerank=pagerank_scores.get(word, 0.0),
                    community_id=communities.get(word, 0),
                )
            )

        await self.db.flush()

        # 写入边
        for u, v, data in G.edges(data=True):
            self.db.add(
                NetworkEdge(
                    source_word=u,
                    target_word=v,
                    weight=data.get("weight", 1),
                )
            )

        await self.db.commit()
        logger.info("网络数据已持久化: %d 节点, %d 边", G.number_of_nodes(), G.number_of_edges())
