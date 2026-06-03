"""
单条评论预测 API 路由

接收原始评论文本，返回完整的 NLP 分析结果。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.services.predictor import PredictorService

router = APIRouter(tags=["单条预测"])


class PredictRequest(BaseModel):
    """预测请求体。"""
    text: str = Field(..., description="待分析的评论文本", min_length=1)


@router.post("/predict")
async def predict_single(
    body: PredictRequest,
    db: AsyncSession = Depends(get_db),
):
    """对单条评论执行完整 NLP 分析流水线。

    接收原始文本，返回：
    - **cleaned_text**: 清洗后的文本
    - **tokens**: jieba 分词结果
    - **snownlp_score**: SnowNLP 情感得分 (0~1)
    - **sentiment_class**: 情感分类 (positive/neutral/negative)
    - **dominant_topic_label**: 主导主题标签
    - **top_keywords**: 匹配到的关键词
    """
    service = PredictorService(db)
    result = await service.predict_single(body.text)
    return APIResponse(data=result)
