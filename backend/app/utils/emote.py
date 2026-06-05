"""
B站表情提取工具

从评论文本中提取方括号格式的表情（如 [doge]、[大哭] 等），
并提供移除表情后的清洗文本。
"""

import re

# 匹配方括号内容: [xxx]
BILIBILI_EMOTE_PATTERN = re.compile(r"\[([^\]]+)\]")

# 合法表情名：仅含中文/字母/数字/下划线
_EMOTE_CHARS = re.compile(r"^[一-鿿\w]+$")

# CJK 字符检测
_CJK = re.compile(r"[一-鿿]")


def _is_valid_emote_name(name: str) -> bool:
    """判断是否为合法表情名。

    规则：仅含中文/字母/数字/下划线，且满足以下之一：
    - 包含至少一个中文字符
    - 长度 >= 2
    单字符 ASCII（如 [1] [!]）不是表情。
    """
    if not _EMOTE_CHARS.match(name):
        return False
    if _CJK.search(name):
        return True
    return len(name) >= 2


def extract_emotes(text: str) -> list[tuple[str, int]]:
    """从原始文本中提取 B站方括号表情。

    Args:
        text: 原始评论文本

    Returns:
        list of (emote_name, position) — 表情名不含括号，position 为起始位置
    """
    if not text:
        return []
    results: list[tuple[str, int]] = []
    for match in BILIBILI_EMOTE_PATTERN.finditer(text):
        name = match.group(1).strip()
        if _is_valid_emote_name(name):
            results.append((name, match.start()))
    return results


def remove_emotes_from_text(text: str) -> str:
    """从文本中移除所有方括号表情，返回清洗后的文本。

    Args:
        text: 原始文本

    Returns:
        移除方括号表情后的文本
    """
    if not text:
        return ""
    return BILIBILI_EMOTE_PATTERN.sub("", text).strip()
