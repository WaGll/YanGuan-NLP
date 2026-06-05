"""语义网络 schema。"""

from pydantic import BaseModel, Field


class NetworkNodeItem(BaseModel):
    """网络节点。"""

    id: str = Field(..., description="节点唯一标识（词语）")
    name: str = Field(..., description="节点显示名称")
    symbolSize: int = Field(..., ge=1, description="节点可视化大小")
    category: int = Field(default=0, ge=0, description="社区类别 ID")
    frequency: int = Field(default=0, ge=0, description="词频")
    degree_centrality: float = Field(default=0.0, ge=0.0, description="度中心性")
    betweenness_centrality: float = Field(default=0.0, ge=0.0, description="介数中心性")
    eigenvector_centrality: float = Field(default=0.0, ge=0.0, description="特征向量中心性")


class NetworkEdgeItem(BaseModel):
    """网络边。"""

    source: str = Field(..., description="源节点词语")
    target: str = Field(..., description="目标节点词语")
    weight: int = Field(..., ge=1, description="边权重（共现次数）")


class NetworkResponse(BaseModel):
    """语义网络图响应。"""

    nodes: list[NetworkNodeItem] = Field(default_factory=list, description="节点列表")
    edges: list[NetworkEdgeItem] = Field(default_factory=list, description="边列表")
    total_nodes: int = Field(default=0, ge=0, description="节点总数")
    total_edges: int = Field(default=0, ge=0, description="边总数")
