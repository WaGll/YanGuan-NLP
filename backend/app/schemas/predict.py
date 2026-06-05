"""实时预测 schema。"""

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """单条预测请求体。"""

    text: str = Field(..., min_length=1, max_length=2000, description="待分析的评论文本")


class PredictResult(BaseModel):
    """单条预测结果。"""

    cleaned_text: str = Field(default="", description="清洗后的文本")
    tokens: list[str] = Field(default_factory=list, description="分词结果")
    snownlp_score: float = Field(default=0.5, ge=0.0, le=1.0, description="SnowNLP 情感得分")
    sentiment_class: str = Field(default="neutral", description="情感分类: positive / neutral / negative")
    dominant_topic_label: str | None = Field(None, description="主导主题标签")
    top_keywords: list[str] = Field(default_factory=list, description="匹配到的 Top 关键词")


class BatchPredictRequest(BaseModel):
    """批量预测请求体。"""

    texts: list[str] = Field(..., min_length=1, max_length=100, description="待分析评论文本列表")


class BatchPredictItem(BaseModel):
    """批量预测单条结果。"""

    index: int = Field(..., ge=0, description="输入列表中的索引位置")
    text: str = Field(..., description="原始文本（截断至 100 字符）")
    result: PredictResult


class BatchPredictResponse(BaseModel):
    """批量预测响应。"""

    items: list[BatchPredictItem] = Field(default_factory=list, description="逐条结果")
    total: int = Field(default=0, ge=0, description="总条数")
    avg_sentiment: float | None = Field(None, description="平均情感得分")
