"""
模块名称：统计持久化服务

功能说明：
    - 累计爬虫统计信息的持久化存储
    - 即使爬虫数据被清空，统计摘要仍保留
    - 关闭软件后重启可恢复历史统计
    - 支持增量更新和重置

存储位置：
    数据目录下的 stats.json 文件
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.paths import get_data_dir

logger = logging.getLogger("tour-crawler.stats_service")

STATS_FILE = "stats.json"

# 默认统计结构
DEFAULT_STATS = {
    "total_tasks_completed": 0,      # 累计完成任务数
    "total_tasks_error": 0,          # 累计出错任务数
    "total_reviews_crawled": 0,      # 累计爬取评论数
    "total_run_seconds": 0,          # 累计运行秒数
    "first_start_at": "",            # 首次使用时间
    "last_completed_at": "",         # 最近一次完成时间
    "sites_used": [],                # 使用过的网站列表
}


class StatsService:
    """
    统计持久化服务。

    管理应用级别的累计统计数据，与爬虫数据独立存储。
    爬虫数据可以被清空，但统计信息会保留。
    """

    def __init__(self):
        self._stats = DEFAULT_STATS.copy()
        self._load()

    # ---- 路径 ----

    def _file_path(self) -> Path:
        return get_data_dir() / STATS_FILE

    # ---- 加载 / 保存 ----

    def _load(self) -> None:
        """从磁盘加载统计数据"""
        path = self._file_path()
        if not path.exists():
            # 首次运行，记录首次使用时间
            self._stats["first_start_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._save()
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并（保留默认结构中的新字段）
            for key, value in saved.items():
                if key in self._stats:
                    self._stats[key] = value
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"加载统计文件失败: {e}")

    def _save(self) -> None:
        """保存统计数据到磁盘"""
        path = self._file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._stats, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"保存统计文件失败: {e}")

    # ---- 读取 ----

    def get_stats(self) -> dict:
        """获取当前统计数据字典"""
        return dict(self._stats)

    # ---- 增量更新 ----

    def record_task_completed(self, review_count: int, site: str = "") -> None:
        """
        记录一个任务完成。

        Args:
            review_count: 本次任务爬取的评论数
            site: 爬取的网站标识
        """
        self._stats["total_tasks_completed"] += 1
        self._stats["total_reviews_crawled"] += review_count
        self._stats["last_completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        if site and site not in self._stats["sites_used"]:
            self._stats["sites_used"].append(site)

        self._save()
        logger.info(f"统计已更新: +1 任务, +{review_count} 评论")

    def record_task_error(self) -> None:
        """记录一个任务出错"""
        self._stats["total_tasks_error"] += 1
        self._save()

    def add_run_seconds(self, seconds: int) -> None:
        """
        累加运行秒数。

        Args:
            seconds: 本次运行增加的秒数
        """
        self._stats["total_run_seconds"] += seconds
        self._save()

    # ---- 重置 ----

    def reset(self) -> None:
        """重置所有统计数据"""
        self._stats = DEFAULT_STATS.copy()
        self._stats["first_start_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._save()
        logger.info("统计数据已重置")

    # ---- 删除文件 ----

    def delete_file(self) -> None:
        """删除统计文件"""
        path = self._file_path()
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning(f"删除统计文件失败: {e}")
