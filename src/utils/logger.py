"""
模块名称：日志记录模块

功能说明：
    - 软件运行日志实时写入 TXT 文件
    - 每次运行生成独立文件（log_YYYY-MM-DD_HHMMSS.txt）
    - 支持 INFO / WARN / ERROR / DEBUG 级别
    - 保留最近 30 天日志，超期自动清理
    - 线程安全（多线程写入同一文件）

依赖模块：
    - logging (标准库)
    - src.utils.paths: get_logs_dir()
"""

import os
import sys
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta

from src.utils.paths import get_logs_dir

# 日志保留天数
LOG_RETENTION_DAYS = 30

# 日志格式：时间 级别 消息
LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 启动时间戳（精确到秒），用于区分每次运行的日志文件
_START_TIME_STR = datetime.now().strftime("%Y-%m-%d_%H%M%S")

# 模块级锁，确保日志轮转和清理线程安全
_lock = threading.Lock()

# 全局 logger 实例缓存
_logger: logging.Logger | None = None


class SingleRunFileHandler(logging.Handler):
    """
    单次运行日志文件处理器。

    每次程序运行生成一个独立的日志文件，文件名格式 log_YYYY-MM-DD_HHMMSS.txt。
    同一运行周期内的所有日志写入同一个文件，不按日期轮转。
    不同运行日志严格分离，互不干扰。
    """

    def __init__(self, logs_dir: Path):
        super().__init__()
        self._logs_dir = logs_dir
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        self.setFormatter(self._formatter)
        # 固定本次运行的日志文件路径（启动时确定，运行期间不变）
        self._log_path = self._logs_dir / f"log_{_START_TIME_STR}.txt"
        # 写入文件头标记
        self._write_header()

    def _write_header(self) -> None:
        """写入日志文件头部信息（首次创建时）"""
        try:
            if not self._log_path.exists():
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(f"程序启动时间: {_START_TIME_STR}\n")
                    f.write("=" * 60 + "\n")
        except OSError:
            pass

    def emit(self, record: logging.LogRecord) -> None:
        """
        写入日志记录到本次运行的日志文件。
        使用追加模式，线程安全由 logging 模块的锁机制保证。
        """
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")
        except OSError:
            # 写入失败时静默处理，不干扰主程序
            pass


def _cleanup_old_logs(logs_dir: Path) -> None:
    """
    清理超过保留期限的旧日志文件。

    扫描 logs 目录下的 log_*.txt 文件，
    从文件名中提取日期部分（YYYY-MM-DD），
    删除早于 LOG_RETENTION_DAYS 天前的文件。

    仅在 logger 初始化时执行一次。
    """
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    if not logs_dir.exists():
        return

    for log_file in logs_dir.glob("log_*.txt"):
        try:
            # 文件名格式: log_YYYY-MM-DD_HHMMSS.txt
            # 提取日期部分（第二个 _ 分段）
            name = log_file.stem
            date_str = name.split("_")[1]  # YYYY-MM-DD
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                log_file.unlink(missing_ok=True)
        except (ValueError, IndexError, OSError):
            # 文件名不符合格式或删除失败，跳过
            continue


def get_logger(name: str = "tour-crawler") -> logging.Logger:
    """
    获取应用日志记录器（单例）。

    每次程序启动生成独立的日志文件，格式 log_YYYY-MM-DD_HHMMSS.txt。
    同一运行期间所有日志写入同一文件，不同运行严格分离。

    Args:
        name: logger 名称，默认 "tour-crawler"

    Returns:
        日志记录器实例

    Example:
        >>> logger = get_logger()
        >>> logger.info("任务创建成功")
        >>> logger.error("网络连接失败", exc_info=True)
    """
    global _logger

    if _logger is not None:
        return _logger

    with _lock:
        # 双重检查锁定
        if _logger is not None:
            return _logger

        logs_dir = get_logs_dir()

        # 清理旧日志
        _cleanup_old_logs(logs_dir)

        # 创建 logger
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.DEBUG)

        # 移除默认 handler，避免重复
        _logger.handlers.clear()

        # 添加文件 handler（本次运行唯一文件）
        file_handler = SingleRunFileHandler(logs_dir)
        _logger.addHandler(file_handler)

        # 同时输出到控制台（仅开发模式）
        if not getattr(sys, 'frozen', False):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
            _logger.addHandler(console_handler)

        # 写入启动标记
        _logger.info("===== 软件启动 =====")

    return _logger


def shutdown_logger() -> None:
    """
    关闭日志记录器，写入结束标记。

    应在应用退出时调用，确保最后一条日志被写入。
    """
    global _logger
    if _logger:
        _logger.info("===== 软件关闭 =====")
        logging.shutdown()
        _logger = None
