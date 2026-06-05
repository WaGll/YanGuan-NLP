"""主题×情感联合分析 schema。"""

from pydantic import BaseModel, Field


class JointMatrixCell(BaseModel):
    """联合矩阵单元格。"""

    topic: str = Field(..., description="主题名称")
    sentiment: str = Field(..., description="情感类别: positive / neutral / negative")
    count: int = Field(..., ge=0, description="该交叉单元的评论数")
    proportion: float = Field(..., ge=0.0, le=1.0, description="占比（0~1）")


class TopicSentimentResponse(BaseModel):
    """主题×情感联合分布矩阵响应。"""

    topics: list[str] = Field(default_factory=list, description="主题标签列表（横轴）")
    topic_business_labels: list[str] = Field(
        default_factory=list, description="业务主题标签列表（优先展示）"
    )
    sentiment_classes: list[str] = Field(
        default_factory=list, description="情感类别列表（纵轴）: positive, neutral, negative"
    )
    cells: list[JointMatrixCell] = Field(default_factory=list, description="矩阵单元格数据")
    total_comments: int = Field(default=0, ge=0, description="参与统计的总评论数")
