"""
模块名称：导出服务

功能说明：
    - 封装导出引擎，提供给 UI 层调用
    - 支持通过 ExportWorker 在线程中异步导出
    - 记录导出历史
"""

import time
import logging
from typing import Optional

from src.models.task import ExportConfig
from src.workers.export_worker import ExportWorker
from src.export import export_reviews
from src.utils.exceptions import ExportError
from src.utils.paths import get_exports_dir

logger = logging.getLogger("tour-crawler.export_service")


class ExportService:
    """
    数据导出服务。

    支持同步导出（直接调用）和异步导出（通过 QThread）。
    """

    def __init__(self):
        self._export_history: list[dict] = []
        self._current_worker: ExportWorker | None = None

    def export_data(
        self,
        reviews: list[dict],
        config: ExportConfig,
    ) -> list[str]:
        """
        同步导出数据（在当前线程执行，适合小数据量）。

        Args:
            reviews: 评论数据
            config: 导出配置

        Returns:
            导出文件路径列表
        """
        paths = []
        for fmt in config.formats:
            try:
                base_path = config.save_path or str(get_exports_dir())
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filepath = f"{base_path}/评论数据_{timestamp}"

                actual_path = export_reviews(reviews, fmt, filepath, config.fields)
                paths.append(actual_path)

                self._add_history(fmt, actual_path, len(reviews))
                logger.info(f"导出成功: {actual_path}")

            except ExportError as e:
                logger.error(f"导出 {fmt} 失败: {e}")

        return paths

    def export_async(self, reviews: list[dict], config: ExportConfig) -> ExportWorker | None:
        """
        异步导出数据（通过 QThread，适合大数据量）。

        Args:
            reviews: 评论数据
            config: 导出配置

        Returns:
            ExportWorker 实例（可用于连接 Signal）
        """
        worker = ExportWorker(reviews, config)
        self._current_worker = worker
        worker.start()
        return worker

    def get_current_worker(self) -> ExportWorker | None:
        """
        获取当前正在运行的导出工作线程。

        Returns:
            ExportWorker 实例或 None
        """
        if self._current_worker and self._current_worker.isRunning():
            return self._current_worker
        return None

    def get_export_history(self) -> list[dict]:
        """
        获取导出历史记录。

        Returns:
            历史记录列表
        """
        return list(self._export_history)

    def _add_history(self, fmt: str, path: str, count: int) -> None:
        """添加导出历史记录"""
        self._export_history.append({
            "format": fmt,
            "path": path,
            "count": count,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
