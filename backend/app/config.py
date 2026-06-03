"""
应用配置模块

使用 pydantic-settings 从环境变量加载配置，所有变量以 GC_ 为前缀。
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """GradCareer 应用全局配置。

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
    data_dir: Path = Path("backend/data")

    # --- 数据库 ---
    database_url: str = "sqlite+aiosqlite:///./gradcareer.db"

    # --- 资源文件路径（若未设置则自动解析到 data_dir 下） ---
    stopwords_path: Optional[Path] = None
    custom_dict_path: Optional[Path] = None
    synonym_path: Optional[Path] = None

    # --- 服务配置 ---
    host: str = "0.0.0.0"
    port: int = 8000
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


# 全局单例配置实例
settings = Settings()
