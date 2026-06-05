"""
表情提取工具测试
"""

import pytest

from app.utils.emote import extract_emotes, remove_emotes_from_text
from app.utils.chinese import clean_chinese_text


class TestExtractEmotes:
    """验证 B站方括号表情提取。"""

    def test_extract_single_emote(self):
        result = extract_emotes("[doge]今天天气不错")
        assert len(result) == 1
        assert result[0][0] == "doge"

    def test_extract_multiple_emotes(self):
        text = "[doge]今天[大哭]很伤心[doge]"
        result = extract_emotes(text)
        assert len(result) == 3
        assert result[0][0] == "doge"
        assert result[1][0] == "大哭"
        assert result[2][0] == "doge"

    def test_extract_emote_with_underscore(self):
        result = extract_emotes("[热词系列_三连]支持一下")
        assert len(result) == 1
        assert result[0][0] == "热词系列_三连"

    def test_extract_tv_emote(self):
        result = extract_emotes("[tv_doge]哈哈哈")
        assert len(result) == 1
        assert result[0][0] == "tv_doge"

    def test_extract_chinese_emote(self):
        result = extract_emotes("[星星眼]好厉害")
        assert len(result) == 1
        assert result[0][0] == "星星眼"

    def test_extract_returns_positions(self):
        text = "前面[doge]中间[大哭]后面"
        result = extract_emotes(text)
        assert len(result) == 2
        assert result[0][1] == 2   # "[doge]" starts at index 2
        assert result[1][1] == 10  # "[大哭]" starts at index 10

    def test_no_emotes_returns_empty(self):
        result = extract_emotes("今天天气不错")
        assert result == []

    def test_empty_text_returns_empty(self):
        assert extract_emotes("") == []
        assert extract_emotes(None) == []  # type: ignore[arg-type]

    def test_ignore_empty_brackets(self):
        # [] has no name content
        result = extract_emotes("[]应该被忽略")
        assert result == []

    def test_false_positive_single_digit(self):
        text = "参考[1]中的说明"
        result = extract_emotes(text)
        # [1] is a single digit, not an emote
        names = [name for name, pos in result]
        assert "1" not in names


class TestRemoveEmotes:
    """验证表情移除。"""

    def test_remove_single_emote(self):
        assert remove_emotes_from_text("[doge]今天天气不错") == "今天天气不错"

    def test_remove_multiple_emotes(self):
        text = "[doge]今天[大哭]很伤心[星星眼]"
        result = remove_emotes_from_text(text)
        assert result == "今天很伤心"

    def test_remove_emotes_only_text(self):
        # All emotes, no real text
        result = remove_emotes_from_text("[doge][大哭][星星眼]")
        assert result == ""

    def test_empty_text(self):
        assert remove_emotes_from_text("") == ""
        assert remove_emotes_from_text(None) == ""  # type: ignore[arg-type]


class TestCleanChineseTextEmotes:
    """验证 clean_chinese_text 集成了表情移除。"""

    def test_emotes_removed_during_cleaning(self):
        text = "[doge]今天天气不错[星星眼]"
        cleaned = clean_chinese_text(text)
        assert "[doge]" not in cleaned
        assert "[星星眼]" not in cleaned
        assert "今天天气不错" in cleaned

    def test_emotes_with_special_chars_removed(self):
        text = "[热词系列_三连]支持up主"
        cleaned = clean_chinese_text(text)
        assert "支持up主" in cleaned
        assert "[热词系列_三连]" not in cleaned

    def test_text_between_emotes_preserved(self):
        text = "[大哭]考研好难[大哭]"
        cleaned = clean_chinese_text(text)
        assert "考研好难" in cleaned
        assert "[大哭]" not in cleaned
