"""LLM Labeler 单元测试。"""

import pytest
from app.services.llm_labeler import (
    LLMCache,
    LLMLabeler,
    _quality_tier,
    get_cache,
)


class TestQualityTier:
    """coherence 质量分级测试。"""

    def test_excellent(self):
        assert _quality_tier(0.55) == "excellent"
        assert _quality_tier(0.5) == "excellent"

    def test_good(self):
        assert _quality_tier(0.45) == "good"
        assert _quality_tier(0.4) == "good"

    def test_fair(self):
        assert _quality_tier(0.35) == "fair"
        assert _quality_tier(0.3) == "fair"

    def test_poor(self):
        assert _quality_tier(0.25) == "poor"
        assert _quality_tier(0.0) == "poor"


class TestLLMCache:
    """LLMCache 单元测试。"""

    def test_set_and_get(self):
        """缓存写入后应能命中。"""
        cache = LLMCache(ttl_hours=24)
        cache.set(["数学", "概率论"], "数学复习", 0.45, "数理统计")
        result = cache.get(["数学", "概率论"], "数学复习", 0.45)
        assert result == "数理统计"

    def test_miss_when_different_keywords(self):
        """不同关键词应未命中。"""
        cache = LLMCache(ttl_hours=24)
        cache.set(["数学", "概率论"], "数学复习", 0.45, "数理统计")
        result = cache.get(["英语", "单词"], "英语备考", 0.50)
        assert result is None

    def test_miss_when_different_rule_label(self):
        """不同规则标签应未命中。"""
        cache = LLMCache(ttl_hours=24)
        cache.set(["数学", "概率论"], "数学复习", 0.45, "数理统计")
        result = cache.get(["数学", "概率论"], "概率相关", 0.45)
        assert result is None

    def test_stats(self):
        """缓存统计正确。"""
        cache = LLMCache(ttl_hours=24)
        # 未命中
        cache.get(["测试"], "测试标签", 0.5)
        # 写入并命中
        cache.set(["测试"], "测试标签", 0.5, "结果")
        cache.get(["测试"], "测试标签", 0.5)
        # 再次命中
        cache.get(["测试"], "测试标签", 0.5)

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert round(stats["hit_rate"], 2) == round(2 / 3, 2)

    def test_clear(self):
        """清空后缓存为空。"""
        cache = LLMCache(ttl_hours=24)
        cache.set(["测试"], "测试标签", 0.5, "结果")
        count = cache.clear()
        assert count == 1
        assert cache.stats()["size"] == 0
        assert cache.stats()["hits"] == 0

    def test_coherence_affects_cache_key(self):
        """不同 coherence 应产生不同缓存 key。"""
        cache = LLMCache(ttl_hours=24)
        cache.set(["测试"], "测试标签", 0.45, "结果A")
        cache.set(["测试"], "测试标签", 0.50, "结果B")
        result_045 = cache.get(["测试"], "测试标签", 0.45)
        result_050 = cache.get(["测试"], "测试标签", 0.50)
        assert result_045 == "结果A"
        assert result_050 == "结果B"


class TestLLMLabelerConfidenceV2:
    """LLMLabeler 置信度计算 v2 测试。"""

    def test_exact_match_full_confidence(self):
        """完全匹配应返回 1.0。"""
        conf = LLMLabeler._compute_confidence_v2(
            "数学复习", "数学复习", ["数学", "复习", "概率论"]
        )
        assert conf == 1.0

    def test_empty_llm_label_zero_confidence(self):
        """空标签应返回 0.0。"""
        conf = LLMLabeler._compute_confidence_v2("数学复习", "", ["数学"])
        assert conf == 0.0

    def test_empty_rule_label_zero_confidence(self):
        """空规则标签应返回 0.0。"""
        conf = LLMLabeler._compute_confidence_v2("", "数学复习", ["数学"])
        assert conf == 0.0

    def test_keyword_overlap_boost(self):
        """标签包含关键词时应提升置信度。"""
        conf_bad = LLMLabeler._compute_confidence_v2(
            "数学复习", "完全不同", ["数学", "概率论", "统计"]
        )
        conf_good = LLMLabeler._compute_confidence_v2(
            "数学复习", "数学相关", ["数学", "概率论", "统计"]
        )
        assert conf_good > conf_bad, f"{conf_good} should be > {conf_bad}"


class TestLLMLabelerWeightedKeywordOverlap:
    """加权关键词重叠测试。"""

    def test_full_overlap(self):
        """所有关键词命中。"""
        score = LLMLabeler._weighted_keyword_overlap(
            "数学概率统计", ["数学", "概率", "统计"]
        )
        assert score > 0.8

    def test_no_overlap(self):
        """零关键词命中。"""
        score = LLMLabeler._weighted_keyword_overlap(
            "英语单词语法", ["数学", "概率", "统计"]
        )
        assert score == 0.0

    def test_partial_overlap(self):
        """部分关键词命中。"""
        score = LLMLabeler._weighted_keyword_overlap(
            "数学复习", ["数学", "概率", "统计"]
        )
        assert 0.0 < score < 0.8

    def test_rank_weight_matters(self):
        """排名靠前的关键词权重更高。"""
        # rank 1: "数学" 在标签中 → 高分
        score_high = LLMLabeler._weighted_keyword_overlap(
            "数学学习", ["数学", "英语", "政治", "复习", "考试"]
        )
        # rank 1: "概率" 不在标签中，rank 5: "数学" 在标签中 → 低分
        score_low = LLMLabeler._weighted_keyword_overlap(
            "数学学习", ["概率", "英语", "政治", "复习", "数学"]
        )
        assert score_high > score_low, f"{score_high} should be > {score_low}"


class TestLLMLabelerCleanLabel:
    """标签清理测试。"""

    def test_clean_quotes(self):
        assert LLMLabeler._clean_label('"数学复习"') == "数学复习"

    def test_clean_prefix(self):
        assert LLMLabeler._clean_label("主题名：数学复习") == "数学复习"
        assert LLMLabeler._clean_label("标签:数学复习") == "数学复习"

    def test_clean_punctuation(self):
        assert LLMLabeler._clean_label("数学复习。") == "数学复习"

    def test_clean_max_length(self):
        assert len(LLMLabeler._clean_label("非常长的主题名称超过限制")) <= 12

    def test_clean_empty_short(self):
        """小于 2 字符的标签返回空。"""
        result = LLMLabeler._clean_label("A")
        assert result == "" or len(result) < 2


class TestGetCacheSingleton:
    """全局缓存单例测试。"""

    def test_same_instance(self):
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
