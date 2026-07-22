"""
模块名称：日志缓冲服务

功能说明：
    - 内存日志缓冲区（deque，最多 10000 条）
    - UILogHandler → 捕获 logging 模块输出到缓冲区
    - Qt Signal → 通知 UI 刷新
    - 支持按 logger name / 级别过滤
    - 支持关键词搜索
"""

import logging
from collections import deque
from datetime import datetime

from PySide6.QtCore import QObject, Signal

# 内存缓冲区最大条数
MAX_LOG_ENTRIES = 10000

# 日志级别 → 显示名称
LEVEL_NAMES = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARN",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class LogEntry:
    """单条日志记录"""

    __slots__ = ("timestamp", "level", "level_name", "logger_name", "message")

    def __init__(self, timestamp: datetime, level: int, level_name: str, logger_name: str, message: str):
        self.timestamp = timestamp
        self.level = level
        self.level_name = level_name
        self.logger_name = logger_name
        self.message = message

    def matches_category(self, category: str) -> bool:
        """
        判断日志是否属于指定分类。

        Args:
            category: "system" | "cookie" | "task" | "crawler" | "export"

        Returns:
            True 表示属于该分类
        """
        name_lower = self.logger_name.lower()
        if category == "cookie":
            return "cookie" in name_lower
        elif category == "task":
            # 任务生命周期管理（创建/删除）+ 执行操作（开始/暂停）
            return any(kw in name_lower for kw in ("task_service", "task_manager"))
        elif category == "crawler":
            # 爬虫核心模块 + 站点适配器 + 任务执行
            return any(kw in name_lower for kw in (
                ".crawler", "crawl_worker", "task_service",
                "stats_service", "captcha_handler", "image_downloader",
                "sites.", "site_service", "notifier", "url_cleaner",
            ))
        elif category == "export":
            # 导出模块：导出服务、导出工作线程
            return any(kw in name_lower for kw in ("export_service", "export_worker"))
        elif category == "system":
            return True  # 系统日志显示全部
        return True


class UILogHandler(logging.Handler):
    """
    自定义 logging Handler，将日志推送到 LogService 的内存缓冲区。

    通过 Qt Signal 通知 UI 层刷新，实现实时日志显示。
    """

    def __init__(self, log_service: "LogService"):
        super().__init__()
        self._service = log_service
        # 不做格式化，仅透传原始消息；时间戳/级别由 UI 层的 append_colored 统一渲染
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        """接收 logging 模块的日志记录，推送到 LogService"""
        try:
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelno,
                level_name=record.levelname,
                logger_name=record.name,
                message=self.format(record),
            )
            self._service.add_entry(entry)
        except Exception:
            # 日志系统自身出错时静默处理
            pass


class LogService(QObject):
    """
    日志缓冲服务（单例）。

    在应用初始化时注册 UILogHandler，所有 logging 输出自动进入内存缓冲区。
    UI 层通过 Signal 订阅日志更新。
    """

    # Qt Signal: 新增日志条目时发射
    entry_added = Signal(LogEntry)

    _instance: "LogService | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._buffer: deque[LogEntry] = deque(maxlen=MAX_LOG_ENTRIES)
        self._handler: UILogHandler | None = None
        self._initialized = True

    def register(self) -> None:
        """
        注册 UILogHandler 到根 logger。

        应在应用启动时调用一次，确保所有后续日志都被捕获。
        """
        if self._handler is not None:
            return  # 已注册

        self._handler = UILogHandler(self)
        self._handler.setLevel(logging.INFO)

        # 根 logger 只记录 INFO 及以上级别
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self._handler)

    def unregister(self) -> None:
        """移除 UILogHandler（应用关闭时调用）"""
        if self._handler is not None:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._handler)
            self._handler = None

    def add_entry(self, entry: LogEntry) -> None:
        """添加日志条目到缓冲区，并发射信号"""
        self._buffer.append(entry)
        self.entry_added.emit(entry)

    def get_entries(
        self,
        category: str = "system",
        levels: set[int] | None = None,
        keyword: str = "",
    ) -> list[LogEntry]:
        """
        获取符合条件的日志条目（从旧到新，依次排列）。

        Args:
            category: "system" | "cookie" | "crawler"
            levels: 允许的日志级别集合，None 表示全部
            keyword: 关键词（不区分大小写）

        Returns:
            匹配的日志条目列表（从旧到新，顶部旧底部新）
        """
        result = []
        kw = keyword.lower().strip() if keyword else ""

        # 先拷贝快照再迭代，避免另一线程同时写入 deque 导致 "mutated during iteration" 崩溃
        for entry in list(self._buffer):
            # 分类过滤
            if not entry.matches_category(category):
                continue
            # 级别过滤
            if levels is not None and entry.level not in levels:
                continue
            # 关键词过滤
            if kw and kw not in entry.message.lower():
                continue
            result.append(entry)

        return result

    def clear(self) -> None:
        """清空内存缓冲区"""
        self._buffer.clear()

    @property
    def total_count(self) -> int:
        """当前缓冲区的日志总数"""
        return len(self._buffer)
