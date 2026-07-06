"""
模块名称：导出工作线程

功能说明：
    - 在 QThread 中执行文件导出操作，不阻塞 UI 主线程
    - 支持单次导出多种格式
    - 通过 Signal 通知导出完成和错误

Signal 接口：
    progress(dict): 导出进度
    complete(dict): 导出完成（包含格式和文件路径）
    error(str): 导出错误
"""

import time
import logging

from PySide6.QtCore import QThread, Signal

from src.export import get_exporter
from src.models.task import ExportConfig
from src.utils.exceptions import ExportError, ExportFormatError
from src.utils.paths import get_exports_dir

logger = logging.getLogger("tour-crawler.export_worker")


class ExportWorker(QThread):
    """
    导出工作线程。

    在独立 QThread 中执行文件导出操作，
    避免大量数据写入时阻塞 UI 响应。

    Usage:
        worker = ExportWorker(reviews, export_config)
        worker.complete.connect(ui.on_export_complete)
        worker.error.connect(ui.on_export_error)
        worker.start()
    """

    # 导出进度
    progress = Signal(dict)

    # 导出完成（包含格式、文件路径等信息）
    complete = Signal(dict)

    # 导出错误
    error = Signal(str)

    def __init__(
        self,
        reviews: list[dict],
        export_config: ExportConfig,
        parent=None,
    ):
        """
        初始化导出工作线程。

        Args:
            reviews: 要导出的评论数据列表
            export_config: 导出配置（格式、路径、字段）
            parent: 父 QObject
        """
        super().__init__(parent)
        self._reviews = list(reviews)
        self._config = export_config
        self._results: list[dict] = []

    def run(self) -> None:
        """
        线程入口。

        按 export_config.formats 列表依次导出每种格式。
        即使某格式导出失败，不影响其他格式继续导出。
        """
        self._results = []

        for fmt in self._config.formats:
            try:
                self._export_single_format(fmt)
            except ExportFormatError as e:
                self.error.emit(str(e))
            except ExportError as e:
                self.error.emit(str(e))
            except Exception as e:
                logger.exception(f"导出 {fmt} 异常")
                self.error.emit(f"导出 {fmt} 失败: {e}")

        # 发送完成通知
        self.complete.emit({
            "results": self._results,
            "total_count": len(self._reviews),
        })

    def _export_single_format(self, fmt: str) -> None:
        """
        导出单种格式。

        Args:
            fmt: 格式名称（"txt" / "csv" / "xlsx" / "docx"）
        """
        import os

        # 构建输出文件路径
        if self._config.save_path:
            # 用户指定了保存路径：去除原扩展名，替换为目标格式扩展名
            base = os.path.splitext(self._config.save_path)[0]
            filepath = base
        else:
            # 未指定路径：使用默认导出目录 + 时间戳
            base_path = str(get_exports_dir())
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filepath = f"{base_path}/评论数据_{timestamp}"

        # 获取导出器并执行导出
        exporter = get_exporter(fmt)
        actual_path = exporter.export(
            reviews=self._reviews,
            filepath=filepath,
            fields=self._config.fields,
        )

        self._results.append({
            "format": fmt,
            "path": actual_path,
            "count": len(self._reviews),
        })

        self.progress.emit({
            "format": fmt,
            "path": actual_path,
            "done": True,
        })

        logger.info(f"导出 {fmt} 完成: {actual_path}")
