"""测试表情分析 API 端点。"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.emote import CommentEmote, EmoteType


@pytest.mark.asyncio
async def test_get_emotes_empty(test_client: AsyncClient):
    """空数据库时返回空列表。"""
    response = await test_client.get("/api/emotes")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["emotes"] == []
    assert data["data"]["total_distinct_emotes"] == 0
    assert data["data"]["total_emote_occurrences"] == 0


@pytest.mark.asyncio
async def test_get_emotes_with_data(
    test_client: AsyncClient, test_db: AsyncSession
):
    """有表情数据时验证频率排序。"""
    # 插入测试数据
    e1 = EmoteType(name="doge", frequency=100, comment_count=80, sentiment="neutral")
    e2 = EmoteType(name="大哭", frequency=200, comment_count=150, sentiment="negative")
    e3 = EmoteType(name="星星眼", frequency=50, comment_count=40, sentiment="positive")
    test_db.add_all([e1, e2, e3])
    await test_db.flush()

    response = await test_client.get("/api/emotes?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200

    emotes = data["data"]["emotes"]
    assert len(emotes) >= 2

    # 按频率降序：大哭(200) > doge(100) > 星星眼(50)
    assert emotes[0]["name"] == "大哭"
    assert emotes[0]["frequency"] == 200

    # 验证情感分布
    breakdown = data["data"]["sentiment_breakdown"]
    assert breakdown["positive"] == 1
    assert breakdown["negative"] == 1
    assert breakdown["neutral"] == 1
    assert breakdown["total"] == 3

    # 验证总统计
    assert data["data"]["total_distinct_emotes"] == 3
    assert data["data"]["total_emote_occurrences"] == 350


@pytest.mark.asyncio
async def test_get_emotes_sort_by_comment_count(
    test_client: AsyncClient, test_db: AsyncSession
):
    """验证按 comment_count 排序。"""
    e1 = EmoteType(name="doge", frequency=100, comment_count=80, sentiment="neutral")
    e2 = EmoteType(name="大哭", frequency=50, comment_count=150, sentiment="negative")
    test_db.add_all([e1, e2])
    await test_db.flush()

    response = await test_client.get("/api/emotes?sort_by=comment_count&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["emotes"][0]["name"] == "大哭"  # 150 > 80


@pytest.mark.asyncio
async def test_get_emotes_sentiment_filter(
    test_client: AsyncClient, test_db: AsyncSession
):
    """验证情感过滤。"""
    e1 = EmoteType(name="大哭", frequency=200, comment_count=150, sentiment="negative")
    e2 = EmoteType(name="星星眼", frequency=50, comment_count=40, sentiment="positive")
    test_db.add_all([e1, e2])
    await test_db.flush()

    response = await test_client.get("/api/emotes?sentiment=negative&limit=10")
    data = response.json()
    emotes = data["data"]["emotes"]
    assert all(e["sentiment"] == "negative" for e in emotes)


@pytest.mark.asyncio
async def test_get_emote_detail_not_found(test_client: AsyncClient):
    """查询不存在的表情返回 404。"""
    response = await test_client.get("/api/emotes/nonexistent")
    assert response.status_code == 200  # APIResponse 包装
    data = response.json()
    assert data["code"] == 404


@pytest.mark.asyncio
async def test_get_emote_detail_with_comments(
    test_client: AsyncClient, test_db: AsyncSession
):
    """验证表情详情含评论样例。"""
    # 插入表情
    e1 = EmoteType(name="doge", frequency=2, comment_count=2, sentiment="neutral")
    test_db.add(e1)
    await test_db.flush()

    # 插入评论
    c1 = Comment(
        comment_id="100001",
        content="[doge]今天天气不错",
        create_time=1717401600,
        video_id="1",
        user_id="1",
        nickname="test_user",
    )
    c2 = Comment(
        comment_id="100002",
        content="厉害了[doge]确实",
        create_time=1717401600,
        video_id="1",
        user_id="2",
        nickname="test_user2",
    )
    test_db.add_all([c1, c2])
    await test_db.flush()

    # 插入关联
    ce1 = CommentEmote(comment_id=c1.id, emote_id=e1.id, position=0)
    ce2 = CommentEmote(comment_id=c2.id, emote_id=e1.id, position=3)
    test_db.add_all([ce1, ce2])
    await test_db.flush()

    response = await test_client.get("/api/emotes/doge")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200

    detail = data["data"]
    assert detail["name"] == "doge"
    assert detail["frequency"] == 2
    assert detail["comment_count"] == 2
    assert detail["sentiment"] == "neutral"
    assert len(detail["sample_comments"]) == 2


@pytest.mark.asyncio
async def test_get_emote_sentiment_correlation(
    test_client: AsyncClient, test_db: AsyncSession
):
    """验证表情-文本情感相关性接口。"""
    response = await test_client.get("/api/emotes/sentiment")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_emote_wordcloud(test_client: AsyncClient, test_db: AsyncSession):
    """验证表情词云接口。"""
    e1 = EmoteType(name="doge", frequency=100, comment_count=80, sentiment="neutral")
    test_db.add(e1)
    await test_db.flush()

    response = await test_client.get("/api/emotes/wordcloud?limit=50")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    items = data["data"]
    assert len(items) >= 1
    assert items[0]["name"] == "doge"
    assert items[0]["value"] == 100


@pytest.mark.asyncio
async def test_get_emote_timeline_not_found(test_client: AsyncClient):
    """查询不存在表情的时间线返回空列表。"""
    response = await test_client.get("/api/emotes/nonexistent/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
