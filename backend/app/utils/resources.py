"""
NLP 资源单例

在应用启动时加载 jieba 词典、停用词表和同义词映射，
提供全局唯一实例供所有服务使用。
"""

import json
from pathlib import Path
from typing import Optional

# 过滤 jieba 的 pkg_resources 弃用警告（jieba/__init__.py 顶层 import 触发）
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

import jieba

# ------------------------------------------------------------------
# Monkey-patch (模块级): 用 importlib.resources 替换 pkg_resources
# ------------------------------------------------------------------
try:
    from importlib.resources import files as _ilr_files
    import jieba._compat as _jieba_compat

    def _patched_get_module_res(*res: str):
        return _ilr_files("jieba").joinpath(*res).open("rb")

    _jieba_compat.get_module_res = _patched_get_module_res
except Exception:
    pass


class NLPResources:
    """NLP 资源单例，持有 jieba 词典、停用词、同义词。

    用法:
        resources = NLPResources.get_instance()
        resources.load(data_dir)
        tokens = [w for w in jieba.lcut(text) if w not in resources.stopwords]
    """

    _instance: Optional["NLPResources"] = None

    def __new__(cls) -> "NLPResources":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "NLPResources":
        """获取全局单例实例。"""
        return cls()

    @property
    def is_loaded(self) -> bool:
        """资源是否已加载。"""
        return self._loaded

    def load(
        self,
        data_dir: Path,
        custom_dict_path: Optional[Path] = None,
        stopwords_path: Optional[Path] = None,
        synonym_path: Optional[Path] = None,
    ) -> None:
        """加载所有 NLP 资源（仅首次调用有效）。

        Args:
            data_dir: 数据目录路径
            custom_dict_path: 自定义词典路径，默认 data_dir/自定义字典.txt
            stopwords_path: 停用词表路径，默认 data_dir/merged_stopwords.txt
            synonym_path: 同义词表路径，默认 data_dir/同义词.txt
        """
        if self._loaded:
            return

        # 加载自定义词典到 jieba
        dict_path = custom_dict_path or data_dir / "自定义字典.txt"
        if dict_path.exists():
            jieba.load_userdict(str(dict_path))

        # 加载停用词
        sw_path = stopwords_path or data_dir / "merged_stopwords.txt"
        self._stopwords: set[str] = set()
        if sw_path.exists():
            with open(sw_path, encoding="utf-8") as f:
                self._stopwords = {line.strip() for line in f if line.strip()}

        # 加载同义词映射 {同义词: 主词}
        sp_path = synonym_path or data_dir / "同义词.txt"
        self._synonyms: dict[str, str] = {}
        if sp_path.exists():
            with open(sp_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.strip().split(",")
                    if len(parts) > 1 and parts[0]:
                        main_word = parts[0]
                        for variant in parts[1:]:
                            if variant:
                                self._synonyms[variant] = main_word

        # 加载表情情感词典 {表情名: 情感标签}
        emote_path = data_dir / "emote_sentiment.txt"
        self._emote_sentiment: dict[str, str] = {}
        if emote_path.exists():
            with open(emote_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.strip().split(",", 1)
                    if len(parts) == 2:
                        self._emote_sentiment[parts[0].strip()] = parts[1].strip()

        self._loaded = True

    @property
    def stopwords(self) -> set[str]:
        """停用词集合。"""
        if not self._loaded:
            raise RuntimeError("NLPResources 尚未加载，请先调用 load()")
        return self._stopwords

    @property
    def synonyms(self) -> dict[str, str]:
        """同义词映射 {variant: canonical}。"""
        if not self._loaded:
            raise RuntimeError("NLPResources 尚未加载，请先调用 load()")
        return self._synonyms

    @property
    def emote_sentiment(self) -> dict[str, str]:
        """表情情感词典 {表情名: positive/negative/neutral}。"""
        if not self._loaded:
            raise RuntimeError("NLPResources 尚未加载，请先调用 load()")
        return self._emote_sentiment

    def get_emote_sentiment(self, emote_name: str) -> str:
        """获取指定表情的情感标签，未收录则返回 neutral。"""
        if not self._loaded:
            raise RuntimeError("NLPResources 尚未加载，请先调用 load()")
        return self._emote_sentiment.get(emote_name, "neutral")

    def replace_synonyms(self, tokens: list[str]) -> list[str]:
        """将 token 列表中的同义词替换为主词。"""
        return [self._synonyms.get(t, t) for t in tokens]
