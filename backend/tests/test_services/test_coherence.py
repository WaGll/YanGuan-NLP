"""CoherenceService 单元测试。"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.coherence import CoherenceService, _quality_tier


class TestQualityTier:
    """coherence 质量分级测试。"""

    def test_excellent(self):
        assert _quality_tier(0.55) == "excellent"

    def test_good(self):
        assert _quality_tier(0.4) == "good"

    def test_fair(self):
        assert _quality_tier(0.3) == "fair"

    def test_poor(self):
        assert _quality_tier(0.1) == "poor"


@pytest.mark.asyncio
class TestCoherenceServiceEmpty:
    """CoherenceService 空数据库测试。"""

    async def test_compare_methods_empty(self, test_db: AsyncSession):
        """空数据库应返回空对比。"""
        service = CoherenceService(test_db)
        result = await service.compare_methods()
        assert result["methods"] == []
        assert result["winner"] is None

    async def test_summary_empty(self, test_db: AsyncSession):
        """空数据库摘要。"""
        service = CoherenceService(test_db)
        result = await service.get_summary()
        assert result["lda"] is None
        assert result["bertopic"] is None
        assert result["mixed_topic_count"] == 0

    async def test_per_comment_coherence_empty(self, test_db: AsyncSession):
        """空数据库逐评论返回 None。"""
        service = CoherenceService(test_db)
        result = await service.get_per_comment_coherence(999)
        assert result is None

    async def test_all_per_comment_coherence_empty(self, test_db: AsyncSession):
        """空数据库批量返回空列表。"""
        service = CoherenceService(test_db)
        result = await service.get_all_per_comment_coherence()
        assert result["items"] == []
        assert result["total"] == 0

    async def test_detect_mixed_topics_empty(self, test_db: AsyncSession):
        """空数据库混合主题返回空列表。"""
        service = CoherenceService(test_db)
        result = await service.detect_mixed_topics()
        assert result == []
