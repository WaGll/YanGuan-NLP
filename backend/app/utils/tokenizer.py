"""
中文分词器抽象层

提供统一的分词接口，支持 pkuseg 和 jieba 两种后端，
通过配置开关切换，pkuseg 不可用时自动降级到 jieba。
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TokenizerBackend(str, Enum):
    """分词后端枚举"""
    PKUSEG = "pkuseg"
    JIEBA = "jieba"


@dataclass
class TokenInfo:
    """单个 Token 的信息

    Attributes:
        word: 词文本
        pos: 词性标签（如 n=名词, v=动词），无词性标注时为空字符串
        is_noise: 是否被判定为噪声词（可用于过滤）
    """
    word: str
    pos: str = ""
    is_noise: bool = False


# ---------------------------------------------------------------------------
# pkuseg 词性标签及噪声规则
# ---------------------------------------------------------------------------
# pkuseg 词性标签集（CTB 简化版）:
#   n 名词    nr 人名    ns 地名    nt 机构名    nz 其他专名
#   v 动词    vd 副动词  vn 名动词
#   a 形容词  ad 副形词  an 名形词
#   d 副词    r 代词    m 数词    q 量词    p 介词
#   c 连词    u 助词    e 叹词    o 拟声词  y 语气词
#   w 标点    x 非语素字  i 成语  j 简称    l 习语

# 噪声词性集合：这些词性的词对主题建模几乎没有贡献
PKUSEG_NOISE_POS: set[str] = {
    "w",   # 标点符号
    "x",   # 非语素字（网名符号、乱码等）
    "u",   # 助词（的、地、得、着、了、过、等）
    "e",   # 叹词（啊、哎、嗯、哦）
    "o",   # 拟声词
    "y",   # 语气词（吧、呢、吗、呀、啦）
    "r",   # 代词（这、那、你、我、他、什么、怎么）
    "p",   # 介词（在、对、从、把、被）
    "c",   # 连词（和、与、或、但是、因为、所以）
    "nr",  # 人名（除非在自定义词典中作为领域专家保留）
    "nrf", # 姓
    "nrg", # 名
}

# jieba 词性标签集噪声集合
JIEBA_NOISE_POS: set[str] = {
    "x",   # 非语素字
    "w",   # 标点符号
    "u",   # 助词
    "e",   # 叹词
    "o",   # 拟声词
    "y",   # 语气词
    "r",   # 代词
    "p",   # 介词
    "c",   # 连词
    "nr",  # 人名
    "nrg", # 名
    "nrf", # 姓
    "m",   # 数词
    "q",   # 量词
}


class ChineseTokenizer:
    """中文分词器，pkuseg 主分词器 + jieba 兜底。

    用法:
        # 使用 pkuseg
        t = ChineseTokenizer(TokenizerBackend.PKUSEG, data_dir=Path("data"))
        tokens = t.tokenize("应用统计学考研怎么准备")
        # → ["应用统计学", "考研", "准备"]

        # 使用 jieba（默认，向后兼容）
        t = ChineseTokenizer(TokenizerBackend.JIEBA, data_dir=Path("data"))
        tokens = t.tokenize("应用统计学考研怎么准备")

        # 带词性标注
        token_infos = t.tokenize_with_pos("茆诗松的概率论")
        # → [TokenInfo(word="茆诗松", pos="nr", is_noise=True), ...]

        # 批量分词
        token_lists = t.tokenize_batch(["文本1", "文本2"])
    """

    def __init__(
        self,
        backend: TokenizerBackend = TokenizerBackend.JIEBA,
        data_dir: Optional[Path] = None,
        user_dict_path: Optional[Path] = None,
        pos_filter: bool = True,
    ):
        """
        Args:
            backend: 分词后端，默认 jieba（向后兼容）
            data_dir: 数据目录，用于加载自定义词典
            user_dict_path: pkuseg 自定义词典路径（每行一个词）
            pos_filter: 是否启用词性噪声标记
        """
        self.backend = backend
        self.pos_filter = pos_filter
        self._pkuseg = None
        self._jieba_loaded = False

        if backend == TokenizerBackend.PKUSEG:
            self._init_pkuseg(data_dir, user_dict_path)
        else:
            self._init_jieba(data_dir)

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _init_pkuseg(self, data_dir: Optional[Path], user_dict_path: Optional[Path]):
        """初始化 pkuseg 分词器，失败时降级到 jieba。"""
        try:
            import spacy_pkuseg
            # 默认使用 web 模型（针对网络文本训练）
            user_dict = str(user_dict_path) if user_dict_path and user_dict_path.exists() else "default"
            self._pkuseg = spacy_pkuseg.pkuseg(
                model_name="web",
                user_dict=user_dict,
                postag=True,  # 启用词性标注以支持噪声过滤
            )
            logger.info("pkuseg (web 模型) 初始化成功，词性标注已启用")
        except Exception as e:
            logger.warning("pkuseg 初始化失败: %s，降级到 jieba", e)
            self.backend = TokenizerBackend.JIEBA
            self._init_jieba(data_dir)

    def _init_jieba(self, data_dir: Optional[Path]):
        """初始化 jieba，确保自定义词典已加载。"""
        # jieba 的自定义词典在 NLPResources.load() 中加载，
        # CleanerService 保证 NLPResources 在构造前已加载，
        # 因此这里只需标记 jieba 可用。
        import jieba
        import jieba.posseg as pseg
        self._jieba_loaded = True
        logger.info("jieba 分词器就绪")

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def tokenize(self, text: str) -> list[str]:
        """分词并返回词列表（不含词性）。

        Args:
            text: 输入文本

        Returns:
            分词后的词列表
        """
        if not text:
            return []

        if self.backend == TokenizerBackend.PKUSEG and self._pkuseg is not None:
            result = self._pkuseg.cut(text)
            # pkuseg with postag returns list of (word, pos) tuples
            if result and isinstance(result[0], tuple):
                tokens = [w for w, pos in result if not self._is_pos_noise(pos)]
            else:
                tokens = result
                tokens = [w for w in tokens if w and len(w.strip()) > 0]
            return tokens
        else:
            # jieba fallback
            import jieba
            return jieba.lcut(text)

    def tokenize_with_pos(self, text: str) -> list[TokenInfo]:
        """分词并返回带词性标注的结果，同时标记噪声词。

        Args:
            text: 输入文本

        Returns:
            TokenInfo 列表，包含词、词性和噪声标记
        """
        if not text:
            return []

        if self.backend == TokenizerBackend.PKUSEG and self._pkuseg is not None:
            result = self._pkuseg.cut(text)
            if result and isinstance(result[0], tuple):
                return [
                    TokenInfo(word=w, pos=pos, is_noise=self._is_pos_noise(pos))
                    for w, pos in result
                ]
            else:
                return [TokenInfo(word=w) for w in result if w and len(w.strip()) > 0]
        else:
            import jieba.posseg as pseg
            return [
                TokenInfo(
                    word=w.word,
                    pos=w.flag,
                    is_noise=self.pos_filter and w.flag in JIEBA_NOISE_POS,
                )
                for w in pseg.cut(text)
            ]

    def tokenize_batch(self, texts: list[str]) -> list[list[str]]:
        """批量分词，兼容现有 CleanerService.tokenize() 接口。

        Args:
            texts: 文本列表

        Returns:
            分词结果列表的列表
        """
        return [self.tokenize(t) for t in texts]

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _is_pos_noise(self, pos: str) -> bool:
        """判断给定词性是否为噪声（对主题建模无贡献）。"""
        if not self.pos_filter:
            return False
        if self.backend == TokenizerBackend.PKUSEG:
            return pos in PKUSEG_NOISE_POS
        else:
            return pos in JIEBA_NOISE_POS

    @property
    def is_pkuseg_available(self) -> bool:
        """pkuseg 是否成功加载并可用。"""
        return self._pkuseg is not None
