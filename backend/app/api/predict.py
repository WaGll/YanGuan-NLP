"""
预测 API 路由

包含 SnowNLP 流水线预测与梯度提升模型预测。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.predict import (
    BatchPredictRequest,
    GBBatchPredictItem,
    GBPredictResult,
    GBTrainResult,
)
from app.services.gb_predictor import (
    list_models,
    predict,
    predict_batch,
    train_models,
)
from app.services.predictor import PredictorService

router = APIRouter(tags=["预测"])


class PredictRequest(BaseModel):
    """SnowNLP 预测请求体。"""
    text: str = Field(..., description="待分析的评论文本", min_length=1)


@router.post("/predict")
async def predict_single(
    body: PredictRequest,
    db: AsyncSession = Depends(get_db),
):
    """对单条评论执行完整 NLP 分析流水线（SnowNLP + LDA 主题推断）。"""
    service = PredictorService(db)
    result = await service.predict_single(body.text)
    return APIResponse(data=result)


# ---- 梯度提升预测端点 ----

@router.post("/predict/gb", response_model=APIResponse[GBPredictResult])
async def predict_gb(
    body: PredictRequest,
    model: str = "best",
):
    """使用梯度提升模型进行单条情感预测。"""
    try:
        result = predict(body.text, model)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return APIResponse(data=GBPredictResult(**result))


@router.post("/predict/gb/batch")
async def predict_gb_batch(
    body: BatchPredictRequest,
    model: str = "best",
):
    """使用梯度提升模型进行批量情感预测。"""
    try:
        items = predict_batch(body.texts, model)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    results = [GBBatchPredictItem(**it) for it in items]
    return APIResponse(data={
        "items": [r.model_dump() for r in results],
        "total": len(results),
    })


@router.post("/predict/gb/train", response_model=APIResponse[GBTrainResult])
async def train_gb():
    """触发梯度提升模型训练（异步执行，可能需要数分钟）。"""
    try:
        result = await train_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"训练失败: {e}")
    return APIResponse(data=GBTrainResult(
        models=result,
        has_trained=len(result) > 0,
    ))


@router.get("/predict/gb/models")
async def list_gb_models():
    """列出已训练的梯度提升模型。"""
    return APIResponse(data=list_models())
