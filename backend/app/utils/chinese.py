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
    # 单字语气词
    "啊", "吧", "呢", "嘛", "呀", "哦", "咯", "呗", "啦",
    "哈", "嗯", "哇", "哟", "噢", "呃", "唉", "喂", "哎",
    # 口语连接词/口头禅
    "这个", "那个", "就是", "然后", "所以说", "反正",
    "怎么说", "话说", "我觉得", "就是说", "怎么说呢",
    "那个啥", "然后呢",
    # B站/评论区特有填充词
    "真的", "确实", "感觉", "觉得", "说实话",
    "讲真的", "说真的", "有一说一", "谁知道",
    "就是说", "我的天", "天呐", "简直",
    # --- 扩充: B站口语化表达 ---
    "真的假的", "太真实了", "笑得", "笑死", "绝了",
    "无敌", "离谱", "绝绝子", "一整个", "咱就是说",
    "就是说呢", "怎么说呢就是", "谁懂", "谁懂啊",
    "家人们", "兄弟们", "xd", "hxd", "u1s1", "y1s1",
    "不是我说", "讲道理", "说句实话", "老实说",
    "这么说吧", "简单来说", "总而言之", "反正就是",
    "就是说啊", "真的就是说", "确实是这样",
    # 低信息量程度副词/连词（在考研评论中无区分度）
    "非常", "特别", "有点", "有点太",
    "真的挺", "真的很", "超级",
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

    # 4. 移除 B站 方括号表情（如 [doge] [大哭] [星星眼] 等）
    # 必须在填充词移除之前执行，避免填充词（如"哈"）清空表情留下空 []
    text = re.sub(r"\[[^\]]+\]", "", text)

    # 5. 移除口语化填充词（逐词直接替换，避免 \b 对中文无效的问题）
    for word in FILLER_WORDS:
        text = text.replace(word, "")

    # 6. 移除常见 emoji 表情
    # 注意：范围必须精确限定在 emoji 区块内，不能覆盖 CJK 汉字区 (U+4E00-U+9FFF)
    text = re.sub(
        r"[\U0001F300-\U0001F5FF"
        r"\U0001F600-\U0001F64F"
        r"\U0001F680-\U0001F6FF"
        r"\U0001F700-\U0001F77F"
        r"\U0001F780-\U0001F7FF"
        r"\U0001F800-\U0001F8FF"
        r"\U0001F900-\U0001F9FF"
        r"\U0001FA00-\U0001FA6F"
        r"\U0001FA70-\U0001FAFF"
        r"\U00002702-\U000027B0"
        r"\U000024C2"
        r"]+",
        "",
        text,
        flags=re.UNICODE,
    )

    # 7. 连续空白压缩为单个空格
    text = re.sub(r"\s+", " ", text)

    # 7. 去除首尾空白
    return text.strip()
