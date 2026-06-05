"""
应用配置模块

使用 pydantic-settings 从环境变量加载配置，所有变量以 GC_ 为前缀。
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# 后端目录的绝对路径，用于构造确定性的数据库和数据路径。
# 使用 Path(__file__).resolve() 确保无论从哪个 CWD 启动进程，
# 始终指向 backend/ 目录。
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    """YanGuan-NLP 应用全局配置。

    所有配置项均从环境变量读取，前缀为 GC_。
    未设置的环境变量将使用此处定义的默认值。
    """

    model_config = SettingsConfigDict(
        env_prefix="GC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 数据目录 ---
    data_dir: Path = _BACKEND_DIR / "data"

    # --- 数据库 ---
    database_url: str = f"sqlite+aiosqlite:///{_BACKEND_DIR / 'gradcareer.db'}"

    # --- 资源文件路径（若未设置则自动解析到 data_dir 下） ---
    stopwords_path: Optional[Path] = None
    custom_dict_path: Optional[Path] = None
    synonym_path: Optional[Path] = None

    # --- BERTopic 模型配置 ---
    bertopic_model_name: str = "shibing624/text2vec-base-chinese"
    bertopic_model_path: Optional[Path] = None  # 本地模型路径，None=自动查找（优先本地 bge-small-zh-v1.5）

    # --- 分词器配置 ---
    tokenizer_backend: str = "jieba"  # "jieba" | "pkuseg"

    # --- 短文本聚合配置 ---
    aggregation_enabled: bool = True  # 是否启用视频+时间窗口聚合
    aggregation_window_minutes: int = 120  # 时间窗口大小（分钟），较大窗口=更多聚合文档→更多主题
    aggregation_min_comments: int = 2  # 最少评论数，低于此阈值的组被丢弃

    # --- Ollama 配置 ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout: float = 120.0  # LLM 调用超时（秒），qwen3 thinking 模式需要更长

    # --- LLM 缓存与批处理配置 ---
    llm_cache_enabled: bool = True  # 启用 LLM 标签结果内存缓存
    llm_cache_ttl_hours: int = 24  # 缓存有效时间（小时）
    llm_batch_size: int = 3  # 单次 LLM 调用最多处理的主题数（thinking 模型需小批次）

    # --- 服务配置 ---
    host: str = "0.0.0.0"
    port: int = 3001
    log_level: str = "INFO"

    def resolve_stopwords_path(self) -> Path:
        """获取停用词文件路径，若未设置则回退到 data_dir/merged_stopwords.txt。"""
        if self.stopwords_path is not None:
            return Path(self.stopwords_path)
        return self.data_dir / "merged_stopwords.txt"

    def resolve_custom_dict_path(self) -> Path:
        """获取自定义词典路径，若未设置则回退到 data_dir/自定义字典.txt。"""
        if self.custom_dict_path is not None:
            return Path(self.custom_dict_path)
        return self.data_dir / "自定义字典.txt"

    def resolve_synonym_path(self) -> Path:
        """获取同义词表路径，若未设置则回退到 data_dir/同义词.txt。"""
        if self.synonym_path is not None:
            return Path(self.synonym_path)
        return self.data_dir / "同义词.txt"

    def resolve_bertopic_model_path(self) -> Path:
        """获取 BERTopic 模型本地路径。

        优先级:
        1. GC_BERTOPIC_MODEL_PATH 环境变量
        2. /home/wg/models/bge-small-zh-v1.5（默认本地模型）
        3. data_dir/model/text2vec（HuggingFace 下载缓存）
        """
        if self.bertopic_model_path is not None:
            return Path(self.bertopic_model_path)
        # 尝试默认本地 bge 模型
        local_bge = Path("/home/wg/models/bge-small-zh-v1.5")
        if (local_bge / "config.json").exists():
            return local_bge
        return self.data_dir / "model" / "text2vec"


# 全局单例配置实例
settings = Settings()
