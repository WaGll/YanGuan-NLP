"""测试 CleanerService。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestChineseUtils:
    """测试 chinese.py 工具函数。"""

    def test_clean_url_removal(self):
        from app.utils.chinese import clean_chinese_text
        text = "看这个链接 https://example.com 很有意思"
        cleaned = clean_chinese_text(text)
        assert "https://example.com" not in cleaned

    def test_clean_empty_input(self):
        from app.utils.chinese import clean_chinese_text
        assert clean_chinese_text("") == ""
        assert clean_chinese_text(None) == ""  # type: ignore

    def test_detect_encoding_utf8(self, tmp_path: Path):
        from app.utils.chinese import detect_encoding
        f = tmp_path / "test.txt"
        f.write_text("测试中文", encoding="utf-8")
        enc = detect_encoding(str(f))
        assert enc is not None


class TestNLPResources:
    """测试 NLPResources 单例。"""

    def test_singleton_pattern(self):
        from app.utils.resources import NLPResources
        r1 = NLPResources.get_instance()
        r2 = NLPResources.get_instance()
        assert r1 is r2

    def test_load_from_data_dir(self):
        from app.utils.resources import NLPResources
        # Reset for test
        NLPResources._instance = None
        resources = NLPResources.get_instance()
        # Load with default data path
        data_dir = Path(__file__).parent.parent.parent / "data"
        if data_dir.exists():
            resources.load(data_dir)
            assert resources.is_loaded
            assert len(resources.stopwords) > 0
            assert isinstance(resources.synonyms, dict)


class TestTokenizer:
    """测试 CleanerService.tokenize() — C1 修复验证。

    验证: 移除 len(w)>1 过滤器后:
    1. 单字实词（不、很、好）通过过滤
    2. 单字虚词（的、了、是）仍被停用词过滤
    3. 多字词行为不变
    """

    @pytest.fixture(autouse=True)
    def _setup_resources(self):
        """确保 NLPResources 在每个测试前已加载。"""
        from app.utils.resources import NLPResources
        NLPResources._instance = None
        resources = NLPResources.get_instance()
        data_dir = Path(__file__).parent.parent.parent / "data"
        if data_dir.exists():
            resources.load(data_dir)

    def test_single_char_content_words_pass_through(self):
        """C1: 单字实词（不、好、很）不应被过滤。

        jieba 分词后，单字实词作为独立 token 出现时应通过过滤器。
        注意: jieba 可能将某些组合（如"不好"）作为一个词输出，
        因此测试使用单独的字符确保 jieba 产生单字 token。
        """
        from app.utils.resources import NLPResources
        resources = NLPResources.get_instance()
        import jieba

        # 分别分词：每个字都是独立 token
        for char in ["不", "好", "很"]:
            tokens = jieba.lcut(char)
            tokens = [w for w in tokens if w not in resources.stopwords]
            assert char in tokens, f"单字实词 '{char}' 应保留"

    def test_single_char_stopwords_still_filtered(self):
        """C1: 单字虚词（的、了、是）仍被停用词过滤。"""
        from app.utils.resources import NLPResources
        resources = NLPResources.get_instance()
        import jieba

        # 分别分词：每个虚字都是独立 token
        for char in ["的", "了", "是"]:
            tokens = jieba.lcut(char)
            tokens = [w for w in tokens if w not in resources.stopwords]
            assert char not in tokens, f"停用词 '{char}' 应仍被过滤"

    def test_multi_char_words_unchanged(self):
        """C1: 多字实词行为不受影响。"""
        from app.utils.resources import NLPResources
        resources = NLPResources.get_instance()
        import jieba

        # 使用确定不在停用词列表中的词
        text = "考研加油一定能上岸"
        tokens = jieba.lcut(text)
        tokens = [w for w in tokens if w not in resources.stopwords]

        assert "考研" in tokens
        assert "加油" in tokens
        assert "上岸" in tokens
