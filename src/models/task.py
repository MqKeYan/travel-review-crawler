"""
模块名称：任务数据模型

功能说明：
    - 定义爬取任务的状态枚举和核心数据结构
    - 任务配置 dataclass（ScrapeConfig、FilterConfig、ExportConfig 等）
    - 任务详情和进度信息结构

设计原则：
    - 所有配置类使用 Python 3.7+ dataclass，提供默认值
    - 可序列化为 JSON，用于保存和恢复任务状态
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    """
    爬取任务状态枚举。

    状态流转：
    pending → running → paused / completed / error
    paused → running（恢复）
    """
    PENDING = "pending"        # 待开始
    RUNNING = "running"        # 运行中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"    # 已完成
    ERROR = "error"            # 出错中断
    CANCELLED = "cancelled"    # 已取消


# ==================== 任务配置类 ====================

@dataclass
class ScrapeConfig:
    """
    爬取配置：控制爬取的范围和停止条件。

    Attributes:
        max_count: 最大爬取条数（默认 500）
        max_pages: 最大翻页数（None 表示不限）
        date_from: 起始日期范围 "YYYY-MM-DD"
        date_to: 结束日期范围 "YYYY-MM-DD"
        rating_min: 最低评分筛选（1~5）
        rating_max: 最高评分筛选（1~5）
        keyword_filter: 关键词列表
        keyword_mode: "include" 只爬包含关键词的 / "exclude" 排除包含关键词的
        delay_seconds: 请求间隔秒数（默认 2.0，越小越快但越容易被反爬）
    """
    max_count: int = 500
    max_pages: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    rating_min: int = 1
    rating_max: int = 5
    keyword_filter: list[str] = field(default_factory=list)
    keyword_mode: str = "include"  # include | exclude
    delay_seconds: float = 2.0


@dataclass
class FilterConfig:
    """
    内容过滤配置：爬取过程中对评论内容的处理规则。

    Attributes:
        remove_images: 是否移除图片标签和链接
        remove_emoji: 是否移除 emoji 字符
        skip_pure_emoji: 是否跳过纯 emoji 评论
        sensitive_words: 敏感词黑名单（命中标记或丢弃）
        ad_filter: 是否启用广告特征词过滤
        filter_action: "mark" 标记 / "discard" 丢弃
    """
    remove_images: bool = False
    remove_emoji: bool = False
    skip_pure_emoji: bool = False
    sensitive_words: list[str] = field(default_factory=list)
    ad_filter: bool = False
    filter_action: str = "discard"  # mark | discard


@dataclass
class ExportConfig:
    """
    导出配置：数据导出时的格式和字段选择。

    Attributes:
        formats: 导出格式列表 ["xlsx", "csv", "txt", "docx"]
        save_path: 保存目录路径
        fields: 需要导出的字段列表
    """
    formats: list[str] = field(default_factory=lambda: ["xlsx", "csv"])
    save_path: str = ""  # 空值表示使用默认导出目录
    fields: list[str] = field(default_factory=lambda: [
        "username", "rating", "content", "time"
    ])


@dataclass
class NotifySetting:
    """
    单事件通知设置。

    Attributes:
        desktop_popup: 桌面弹窗
        sound: 声音提示
        pushplus_token: PushPlus 推送 token（空则不推送）
    """
    desktop_popup: bool = False
    sound: bool = False
    pushplus_token: str = ""


@dataclass
class NotifyConfig:
    """
    通知配置：不同事件的通知行为。

    Attributes:
        on_complete: 任务完成时的通知设置
        on_error: 任务出错时的通知设置
    """
    on_complete: NotifySetting = field(default_factory=NotifySetting)
    on_error: NotifySetting = field(default_factory=NotifySetting)


@dataclass
class TaskConfig:
    """
    完整任务配置：创建爬取任务所需的全部参数。

    Attributes:
        task_name: 任务名称（用户自定义，如 "黄山风景区评论"）
        site: 网站标识（"ctrip"、"dianping" 等）
        target_url: 目标景区评论页面 URL
        cookie_file: Cookie 文件名（如 "ctrip.json"），空则不使用 Cookie
        scrape_config: 爬取范围配置
        filter_config: 内容过滤配置
        export_config: 导出配置
        notify_config: 通知配置
    """
    task_name: str = ""
    site: str = ""
    target_url: str = ""
    cookie_file: str = ""
    scrape_config: ScrapeConfig = field(default_factory=ScrapeConfig)
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    export_config: ExportConfig = field(default_factory=ExportConfig)
    notify_config: NotifyConfig = field(default_factory=NotifyConfig)


# ==================== 任务运行时结构 ====================

@dataclass
class TaskProgress:
    """
    任务实时进度信息。

    由 CrawlWorker 通过 Qt Signal 推送到 UI。

    Attributes:
        current: 当前已爬取条数
        total: 目标条数
        percentage: 完成百分比 (0~100)
        current_page: 当前页码
        message: 状态描述文本
        speed: 爬取速度描述（"12条/分钟"）
        eta: 预计剩余时间描述（"约31分钟"）
    """
    current: int = 0
    total: int = 0
    percentage: float = 0.0
    current_page: int = 0
    message: str = ""
    speed: str = ""
    eta: str = ""


@dataclass
class Task:
    """
    任务实体：运行时任务完整信息。

    对应 tasks/ 目录下的任务进度 JSON 和内存中的任务状态。
    """

    task_id: str = ""
    task_name: str = ""
    site: str = ""
    site_display_name: str = ""
    target_url: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    config: TaskConfig = field(default_factory=TaskConfig)
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_reviews: int = 0

    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON 存储）"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "site": self.site,
            "site_display_name": self.site_display_name,
            "target_url": self.target_url,
            "status": self.status.value,
            "total_reviews": self.total_reviews,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "config": self._config_to_dict(),
            "progress": self._progress_to_dict(),
        }

    def _config_to_dict(self) -> dict:
        """将任务配置序列化为字典"""
        return asdict(self.config)

    def _progress_to_dict(self) -> dict:
        """将任务进度序列化为字典"""
        return {
            "current": self.progress.current,
            "total": self.progress.total,
            "percentage": self.progress.percentage,
            "current_page": self.progress.current_page,
            "message": self.progress.message,
            "speed": self.progress.speed,
            "eta": self.progress.eta,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """从字典反序列化重建 Task 对象"""
        # 重建进度
        progress_data = data.get("progress", {})
        progress = TaskProgress(
            current=progress_data.get("current", 0),
            total=progress_data.get("total", 0),
            percentage=progress_data.get("percentage", 0.0),
            current_page=progress_data.get("current_page", 0),
            message=progress_data.get("message", ""),
            speed=progress_data.get("speed", ""),
            eta=progress_data.get("eta", ""),
        )

        # 重建配置
        cfg = data.get("config", {})
        scrape = cfg.get("scrape_config", {})
        filter_ = cfg.get("filter_config", {})
        export_ = cfg.get("export_config", {})
        notify_ = cfg.get("notify_config", {})

        scrape_config = ScrapeConfig(
            max_count=scrape.get("max_count", 500),
            max_pages=scrape.get("max_pages"),
            date_from=scrape.get("date_from"),
            date_to=scrape.get("date_to"),
            rating_min=scrape.get("rating_min", 1),
            rating_max=scrape.get("rating_max", 5),
            keyword_filter=scrape.get("keyword_filter", []),
            keyword_mode=scrape.get("keyword_mode", "include"),
            delay_seconds=scrape.get("delay_seconds", 2.0),
        )

        filter_config = FilterConfig(
            remove_images=filter_.get("remove_images", False),
            remove_emoji=filter_.get("remove_emoji", False),
            skip_pure_emoji=filter_.get("skip_pure_emoji", False),
            sensitive_words=filter_.get("sensitive_words", []),
            ad_filter=filter_.get("ad_filter", False),
            filter_action=filter_.get("filter_action", "discard"),
        )

        export_config = ExportConfig(
            formats=export_.get("formats", ["xlsx", "csv"]),
            save_path=export_.get("save_path", ""),
            fields=export_.get("fields", [
                "username", "rating", "content", "time"
            ]),
        )

        notify_on_complete = notify_.get("on_complete", {})
        notify_on_error = notify_.get("on_error", {})
        notify_config = NotifyConfig(
            on_complete=NotifySetting(
                desktop_popup=notify_on_complete.get("desktop_popup", True),
                sound=notify_on_complete.get("sound", True),
                pushplus_token=notify_on_complete.get("pushplus_token", ""),
            ),
            on_error=NotifySetting(
                desktop_popup=notify_on_error.get("desktop_popup", True),
                sound=notify_on_error.get("sound", True),
                pushplus_token=notify_on_error.get("pushplus_token", ""),
            ),
        )

        task_config = TaskConfig(
            task_name=data.get("task_name", ""),
            site=data.get("site", ""),
            target_url=data.get("target_url", ""),
            cookie_file=cfg.get("cookie_file", ""),
            scrape_config=scrape_config,
            filter_config=filter_config,
            export_config=export_config,
            notify_config=notify_config,
        )

        # 反序列化状态
        status_str = data.get("status", "pending")
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.PENDING

        return cls(
            task_id=data.get("task_id", data.get("task_name", "")),
            task_name=data.get("task_name", ""),
            site=data.get("site", ""),
            site_display_name=data.get("site_display_name", ""),
            target_url=data.get("target_url", ""),
            status=status,
            progress=progress,
            config=task_config,
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            total_reviews=data.get("total_reviews", 0),
        )

    def update_progress_from_dict(self, progress_data: dict) -> None:
        """从爬虫进度数据字典更新任务进度"""
        self.progress.current = progress_data.get("current", self.progress.current)
        self.progress.total = progress_data.get("total", self.progress.total)
        self.progress.percentage = progress_data.get("percentage", self.progress.percentage)
        self.progress.current_page = progress_data.get("current_page", self.progress.current_page)
        self.progress.message = progress_data.get("message", self.progress.message)
        self.progress.speed = progress_data.get("speed", self.progress.speed)
        self.progress.eta = progress_data.get("eta", self.progress.eta)
