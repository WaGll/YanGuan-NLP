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
