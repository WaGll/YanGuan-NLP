"""
数据加载服务

负责将 CSV 文件批量导入到 comments 表。
修复了旧代码中的关键问题：
  - 只读取 content 列 → 现在读取全部列，防止字段数据丢失
  - \\b 正则对中文无效 → 改用逐词替换清洗
  - 临时文件竞态条件 → 直接流式读取 CSV
  - 逐行查重 → 使用 INSERT OR IGNORE 批量插入
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import chardet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.utils.chinese import clean_chinese_text

logger = logging.getLogger(__name__)

# 批量插入的批次大小
BATCH_SIZE = 500


class DataLoaderService:
    """CSV 数据导入服务。

    读取评论 CSV 文件，解析所有列（修复了仅读取 content 列导致数据丢失的 bug），
    使用 INSERT OR IGNORE 策略批量写入，避免逐行查询的性能问题。
    """

    def __init__(self, db: AsyncSession) -> None:
        """初始化数据加载服务。

        Args:
            db: 异步数据库会话
        """
        self.db = db

    async def import_csv(self, file_path: str | Path) -> dict[str, int]:
        """从 CSV 文件导入评论数据到 comments 表。

        自动检测编码，读取全部列，将 Unix 时间戳转换为 datetime，
        清洗评论内容后批量写入。

        Args:
            file_path: CSV 文件路径

        Returns:
            导入统计: {"rows_imported": N, "skipped": N}

        Raises:
            FileNotFoundError: 文件不存在时抛出
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检测文件编码
        encoding = self._detect_encoding(file_path)
        logger.info("检测到文件编码: %s，开始导入: %s", encoding, file_path.name)

        rows_imported = 0
        skipped = 0
        batch: list[dict[str, Any]] = []

        with open(file_path, encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # 第 1 行为表头
                try:
                    comment_data = self._parse_row(row)
                    if comment_data is None:
                        skipped += 1
                        continue

                    batch.append(comment_data)

                    if len(batch) >= BATCH_SIZE:
                        count = await self._flush_batch(batch)
                        rows_imported += count
                        batch.clear()
                        logger.info("已导入 %d 条记录...", rows_imported)

                except Exception as e:
                    logger.warning("第 %d 行解析失败: %s", row_num, e)
                    skipped += 1

            # 刷新剩余批次
            if batch:
                count = await self._flush_batch(batch)
                rows_imported += count

        logger.info("导入完成: 成功 %d 条，跳过 %d 条", rows_imported, skipped)
        return {"rows_imported": rows_imported, "skipped": skipped}

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_encoding(file_path: Path) -> str:
        """使用 chardet 检测文件编码，带回退机制。"""
        try:
            with open(file_path, "rb") as f:
                raw = f.read(1024 * 1024)  # 前 1MB
            result = chardet.detect(raw)
            encoding = result.get("encoding", "utf-8")
            if encoding is None:
                encoding = "utf-8"
            if encoding.upper() in ("GB2312", "GB18030"):
                encoding = "gbk"
            return encoding
        except Exception:
            return "utf-8"

    def _parse_row(self, row: dict[str, Any]) -> dict[str, Any] | None:
        """从 CSV 行解析 Comment 数据字典。

        读取所有原始列，修复了旧代码中仅读取 content 列的 bug。
        返回 None 表示该行应被跳过（如缺少 comment_id）。

        Args:
            row: csv.DictReader 返回的一行数据

        Returns:
            可用于 INSERT 的数据字典，或 None
        """
        comment_id = str(row.get("comment_id", "")).strip()
        if not comment_id:
            return None

        content = str(row.get("content", "")).strip() if row.get("content") else ""

        # 解析 Unix 时间戳（秒级或毫秒级）
        create_time = self._parse_int(row.get("create_time"))
        create_datetime = None
        if create_time is not None and create_time > 0:
            try:
                ts = create_time
                # 毫秒级时间戳 → 转换为秒
                if ts > 1e12:
                    ts = ts // 1000
                create_datetime = datetime.fromtimestamp(ts)
            except (OSError, ValueError):
                create_datetime = None

        # 清洗评论文本
        cleaned = clean_chinese_text(content) if content else None

        return {
            "comment_id": comment_id,
            "parent_comment_id": str(row.get("parent_comment_id", "")).strip() or None,
            "create_time": create_time or 0,
            "create_datetime": create_datetime,
            "video_id": str(row.get("video_id", "")).strip() or None,
            "content": content or None,
            "user_id": str(row.get("user_id", "")).strip() or None,
            "nickname": str(row.get("nickname", "")).strip() or None,
            "avatar": str(row.get("avatar", "")).strip() or None,
            "sub_comment_count": self._parse_int(row.get("sub_comment_count")),
            "last_modify_ts": self._parse_int(row.get("last_modify_ts")),
            "cleaned_content": cleaned,
        }

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        """安全地将字段值解析为 int，失败返回 None。"""
        if value is None:
            return None
        try:
            val = str(value).strip()
            if not val:
                return None
            return int(float(val))
        except (ValueError, TypeError):
            return None

    async def _flush_batch(self, batch: list[dict[str, Any]]) -> int:
        """将一批数据字典批量写入数据库。

        使用 INSERT OR IGNORE 避免重复导入（依赖 comment_id 唯一约束），
        替代旧代码中的逐行 SELECT 查重，大幅提升性能。

        Args:
            batch: 数据字典列表

        Returns:
            成功插入的记录数
        """
        if not batch:
            return 0

        columns = [
            "comment_id", "parent_comment_id", "create_time", "create_datetime",
            "video_id", "content", "user_id", "nickname", "avatar",
            "sub_comment_count", "last_modify_ts", "cleaned_content",
        ]
        placeholders = ", ".join([f":{col}" for col in columns])
        col_names = ", ".join(columns)

        stmt = text(
            f"INSERT OR IGNORE INTO comments ({col_names}) VALUES ({placeholders})"
        )

        result = await self.db.execute(stmt, batch)  # type: ignore[arg-type]
        await self.db.commit()

        return result.rowcount if result.rowcount else len(batch)
