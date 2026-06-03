"""
中文文本处理工具

提供编码检测、文本清洗等中文 NLP 预处理功能。
修复了旧代码中使用 \\b 正则边界（对中文无效）等问题。
"""

import re
from pathlib import Path

import chardet

# =============================================================================
# 中文口语化填充词列表（可根据业务需要扩充）
# =============================================================================
FILLER_WORDS: list[str] = [
    "啊", "吧", "呢", "嘛", "呀", "哦", "咯", "呗", "啦",
    "哈", "嗯", "哇", "哟", "噢", "呃", "唉", "喂", "哎",
    "这个", "那个", "就是", "然后", "所以说", "反正",
    "怎么说", "话说", "我觉得", "就是说", "怎么说呢",
    "那个啥", "然后呢",
]


def detect_encoding(file_path: str | Path) -> str:
    """检测文本文件编码。

    读取文件前 1MB 使用 chardet 推测编码，自动将 GB2312/GB18030 映射为 GBK。

    Args:
        file_path: 文件路径

    Returns:
        检测到的编码名称（如 'utf-8', 'gbk' 等），默认为 'utf-8'
    """
    file_path = Path(file_path)
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read(1024 * 1024)  # 读取前 1MB 用于检测
        result = chardet.detect(raw_data)
        encoding = result.get("encoding", "utf-8")
        if encoding is None:
            encoding = "utf-8"
        # GB2312 / GB18030 统一视为 GBK 以兼容更多字符
        if encoding.upper() in ("GB2312", "GB18030"):
            encoding = "gbk"
        return encoding
    except Exception:
        return "utf-8"


def clean_chinese_text(text: str) -> str:
    """清洗中文评论文本。

    执行以下清洗步骤：
    1. 移除 URL 链接
    2. 移除 HTML 标签
    3. 移除 @提及 和 #话题#
    4. 使用 str.replace 移除口语化填充词
       （修复了旧代码 re.sub(r"\\b...\\b") 对中文无效的 bug）
    5. 移除常见 emoji 表情
    6. 将连续空白归一化为单个空格
    7. 去除首尾空白

    Args:
        text: 原始评论文本

    Returns:
        清洗后的文本，空输入返回空字符串
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. 移除 URL
    text = re.sub(r"https?://\S+", "", text)

    # 2. 移除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)

    # 3. 移除 @提及 和 #话题#
    text = re.sub(r"@\S+", "", text)
    text = re.sub(r"#\S+#", "", text)

    # 4. 移除口语化填充词（逐词直接替换，避免 \\b 对中文无效的问题）
    for word in FILLER_WORDS:
        text = text.replace(word, "")

    # 5. 移除常见 emoji 表情
    text = re.sub(
        r"[\U0001F600-\U0001F64F"
        r"\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF"
        r"\U00002702-\U000027B0"
        r"\U000024C2-\U0001F251"
        r"]+",
        "",
        text,
        flags=re.UNICODE,
    )

    # 6. 连续空白压缩为单个空格
    text = re.sub(r"\s+", " ", text)

    # 7. 去除首尾空白
    return text.strip()
