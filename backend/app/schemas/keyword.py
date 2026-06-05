"""关键词与词云 schema。"""

from pydantic import BaseModel, Field


class KeywordItem(BaseModel):
    """单个关键词条目。"""

    word: str = Field(..., description="关键词")
    frequency: int = Field(..., ge=0, description="词频")
    tfidf_score: float | None = Field(None, description="TF-IDF 得分")


class WordcloudItem(BaseModel):
    """词云数据条目（name + value 格式）。"""

    name: str = Field(..., description="词语")
    value: int = Field(..., ge=0, description="词频值")


class KeywordsResponse(BaseModel):
    """关键词列表 + 词云数据响应。"""

    keywords: list[KeywordItem] = Field(default_factory=list)
    wordcloud_data: list[WordcloudItem] = Field(default_factory=list)
    total: int = Field(default=0, ge=0, description="关键词总数")
