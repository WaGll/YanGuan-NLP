"""测试单条评论预测 API 端点。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_predict_single(test_client: AsyncClient):
    """测试单条评论预测返回完整分析结果。"""
    response = await test_client.post(
        "/api/predict",
        json={"text": "数学太难了，但是统计学很有意思"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    result = data["data"]
    # 验证返回字段
    assert "cleaned_text" in result
    assert "tokens" in result
    assert "snownlp_score" in result
    assert "sentiment_class" in result
    # SnowNLP 分数应在 0~1 之间
    assert 0 <= result["snownlp_score"] <= 1
    # 情感分类应为三个类别之一
    assert result["sentiment_class"] in ("positive", "neutral", "negative")


@pytest.mark.asyncio
async def test_predict_empty_text(test_client: AsyncClient):
    """测试空文本被拒绝（422 参数错误）。"""
    response = await test_client.post(
        "/api/predict",
        json={"text": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_no_body(test_client: AsyncClient):
    """测试缺失请求体被拒绝（422）。"""
    response = await test_client.post("/api/predict")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_predict_chinese_negative(test_client: AsyncClient):
    """测试负面中文评论的预测结果。"""
    response = await test_client.post(
        "/api/predict",
        json={"text": "考研太难了，完全没希望，好绝望"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    result = data["data"]
    # 清洗后文本可能为空（全为停用词），但 tokens 列表应存在
    assert isinstance(result["cleaned_text"], str)
    assert isinstance(result["tokens"], list)


@pytest.mark.asyncio
async def test_predict_chinese_positive(test_client: AsyncClient):
    """测试正面中文评论的预测结果。"""
    response = await test_client.post(
        "/api/predict",
        json={"text": "加油！一定能考上理想的学校！"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    result = data["data"]
    assert result["snownlp_score"] > 0  # 正面应得分 > 0
