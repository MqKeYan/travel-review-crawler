"""
数据模型包，定义应用中使用的数据结构。

包含：
    - task.py: 爬取任务数据模型及配置 dataclass
    - review.py: 评论数据模型
"""

from src.models.task import (
    Task,
    TaskStatus,
    TaskConfig,
    ScrapeConfig,
    FilterConfig,
    ExportConfig,
    NotifyConfig,
    NotifySetting,
)
from src.models.review import Review, ReviewStats, PageResult

__all__ = [
    "Task", "TaskStatus", "TaskConfig",
    "ScrapeConfig", "FilterConfig", "ExportConfig",
    "NotifyConfig", "NotifySetting",
    "Review", "ReviewStats", "PageResult",
]
