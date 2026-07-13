"""
模块名称：爬取工作线程

功能说明：
    - 在 QThread 中运行爬虫任务，不阻塞 UI 主线程
    - 通过 Qt Signal 实时推送爬取进度到 UI
    - 支持任务的启动、暂停、恢复、停止
    - 集成过滤器和断点续爬机制

Signal 接口：
    progress(dict): 爬取进度（当前/总数/百分比/页码/消息/速度/ETA）
    log(str): 日志消息
    error(str): 错误消息
    complete(dict): 任务完成汇总（评论数、耗时等）
"""

import time
import json
import logging

from PySide6.QtCore import QThread, Signal

from src.engine.crawler import crawl_all_pages
from src.sites import get_site_adapter
from src.filters import build_filter_chain
from src.models.task import TaskConfig
from src.utils.paths import get_tasks_dir

logger = logging.getLogger("tour-crawler.crawl_worker")


class CrawlWorker(QThread):
    """
    爬取工作线程。

    在独立的 QThread 中运行爬虫引擎，将原始 HTTP 响应解析为标准评论数据，
    经过过滤器链处理后通过 Signal 推送到 UI 层。

    Usage:
        worker = CrawlWorker(task_config)
        worker.progress.connect(ui.on_progress)
        worker.complete.connect(ui.on_complete)
        worker.error.connect(ui.on_error)
        worker.start()
    """

    # ==================== Qt Signals ====================
    # 爬取进度（包含当前条数、总数、百分比、页码、消息）
    progress = Signal(dict)

    # 日志消息（文本字符串）
    log = Signal(str)

    # 错误消息（文本字符串）
    error = Signal(str)

    # 任务完成（包含评论列表、总条数、耗时等信息）
    complete = Signal(dict)

    def __init__(self, task_config: TaskConfig, parent=None, notifier=None):
        """
        初始化爬取工作线程。

        Args:
            task_config: 完整的任务配置
            parent: 父 QObject
            notifier: 通知器实例（用于验证码通知等）
        """
        super().__init__(parent)
        self._config = task_config
        self._notifier = notifier

        # 爬取到的评论数据缓存
        self._reviews: list[dict] = []

        # 控制标志
        self._paused = False          # 暂停标志
        self._stopped = False         # 停止标志
        self._is_running = False      # 运行状态
        self._driver = None           # Selenium driver 引用，供外部清理

        # 断点信息
        self._resume_page = 0         # 断点续爬的起始页码
        self._resume_count = 0        # 断点续爬的已有条数

        # 计时
        self._start_time: float = 0.0

        # 构建过滤器链
        filter_config = self._config.filter_config
        self._filter_chain = build_filter_chain(filter_config)

    def run(self) -> None:
        """
        线程入口（由 QThread.start() 自动调用）。

        执行爬取主流程：初始化 → 断点检测 → 爬取循环 → 完成通知。
        """
        self._is_running = True
        self._start_time = time.time()

        task_id = self._config.task_name  # 简单起见，用任务名做标识
        self._log_message(f"任务 [{task_id}] 开始爬取")

        try:
            # ---- Cookie 状态 ----
            if self._config.cookie_file:
                self._log_message(f"任务 [{task_id}] 使用 Cookie: {self._config.cookie_file}")
            else:
                self._log_message(f"任务 [{task_id}] 未配置 Cookie，将无登录态爬取")

            # ---- 检查断点 ----
            self._check_resume_point()
            if self._resume_page > 1:
                self._log_message(f"任务 [{task_id}] 检测到断点，从第 {self._resume_page} 页继续")

            # ---- 获取网站适配器 ----
            adapter = get_site_adapter(self._config.site)
            if adapter is None:
                self._emit_error(f"不支持的网站: {self._config.site}")
                return

            # Selenium 模式提示（worker 层输出，确保暂停恢复不重复）
            if adapter.selenium_crawler and self._config.target_url:
                scrape_cfg = self._config.scrape_config
                page_limit = scrape_cfg.max_pages or adapter.max_pages_limit
                if page_limit > 1:
                    self._log_message(f"任务 [{task_id}] 使用 Selenium 翻页爬取")

            # ---- 爬取主循环 ----
            def progress_callback(page_num=None, count=None, total=None, error=None, message=""):
                """爬取进度回调（从爬虫引擎的 crawl_all_pages 调用）。
                count/total 均为过滤后通过的数量。"""
                if error:
                    self._emit_error(error)
                    return

                total_count = self._resume_count + total
                scrape_config = self._config.scrape_config
                target = scrape_config.max_count or 0

                progress_data = {
                    "current": total_count,
                    "total": target if target > 0 else total_count,
                    "percentage": min(int(total_count / target * 100), 100) if target > 0 else 0,
                    "current_page": page_num or 0,
                    "message": message or (f"正在爬取第 {page_num} 页..." if page_num else ""),
                    "speed": self._calculate_speed(total_count),
                    "eta": self._calculate_eta(total_count, target),
                }
                self.progress.emit(progress_data)

            # 传递 driver 引用，供外部在异常情况下清理浏览器
            driver_ref: list = []
            self._driver = driver_ref

            reviews, rejected_count = crawl_all_pages(
                adapter=adapter,
                cookie_file=self._config.cookie_file,
                max_pages=self._config.scrape_config.max_pages,
                max_count=self._config.scrape_config.max_count,
                progress_callback=progress_callback,
                stop_check=self._is_stopped,
                target_url=self._config.target_url,
                delay_seconds=self._config.scrape_config.delay_seconds,
                filter_chain=self._filter_chain,
                task_name=task_id,
                driver_ref=driver_ref,
                notifier=self._notifier,
            )

            self._reviews = reviews

            # ---- 下载评论图片到本地 ----
            # 如果用户勾选了"移除图片"，跳过下载
            if self._config.filter_config.remove_images:
                self._log_message(f"任务 [{task_id}] 已启用移除图片，跳过图片下载")
            elif not self._stopped and self._reviews:
                try:
                    from src.engine.image_downloader import download_images_for_task

                    # 构建下载进度回调，显示"下载图片"而非"正在爬取"
                    def _download_progress(page_num=None, count=None, total=None, message="", error=None):
                        if error:
                            return
                        reviews_with_images = sum(1 for r in self._reviews if r.get("image_urls"))
                        progress_data = {
                            "current": total or 0,
                            "total": reviews_with_images,
                            "percentage": int((total or 0) / max(reviews_with_images, 1) * 100),
                            "current_page": 0,
                            "message": message or "下载图片中...",
                            "speed": "",
                            "eta": "",
                        }
                        self.progress.emit(progress_data)

                    download_images_for_task(
                        reviews=self._reviews,
                        task_name=self._config.task_name,
                        progress_callback=_download_progress,
                    )
                except Exception as e:
                    logger.warning(f"图片下载出错（评论数据不受影响）: {e}")

            # ---- 完成 ----
            elapsed = time.time() - self._start_time
            elapsed_str = f"{elapsed:.0f}秒" if elapsed < 60 else f"{elapsed/60:.1f}分钟"

            self._log_message(f"任务 [{task_id}] 完成，共 {len(self._reviews)} 条，耗时 {elapsed_str}")

            self.complete.emit({
                "task_name": self._config.task_name,
                "reviews": self._reviews,
                "count": len(self._reviews),
                "rejected_count": rejected_count,
                "elapsed": elapsed_str,
            })

        except Exception as e:
            logger.exception(f"任务 [{task_id}] 爬取线程异常")
            self._emit_error(f"爬取异常: {e}")

        finally:
            self._is_running = False

    # ==================== 控制方法 ====================

    def pause(self) -> None:
        """暂停爬取任务"""
        self._paused = True
        self._log_message(f"任务 [{self._config.task_name}] 已暂停")

    def resume(self) -> None:
        """恢复暂停的爬取任务"""
        self._paused = False
        self._log_message(f"任务 [{self._config.task_name}] 已恢复")

    def stop(self) -> None:
        """停止爬取任务"""
        self._stopped = True
        self._paused = False
        self._log_message(f"任务 [{self._config.task_name}] 正在停止...")

    @property
    def is_running(self) -> bool:
        """线程是否正在运行"""
        return self._is_running

    @property
    def collected_reviews(self) -> list[dict]:
        """获取已爬取的评论数据"""
        return list(self._reviews)

    # ==================== 内部方法 ====================

    def _is_stopped(self) -> bool:
        """
        停止检测函数（供爬虫引擎回调）。

        当用户暂停/停止时返回 True，爬虫引擎应停止翻页。
        暂停时循环等待，不真正停止。
        """
        if self._stopped:
            return True
        # 暂停逻辑：循环等待直到恢复或停止
        while self._paused and not self._stopped:
            QThread.msleep(200)  # 200ms 检查一次
        return self._stopped

    def _check_resume_point(self) -> None:
        """
        检查是否存在断点续爬文件。

        如果存在，读取已保存的进度信息，设置 resume_page 和 resume_count。
        进度文件格式见软件大纲 4.7.0 节。
        """
        # 使用任务名生成断点文件路径
        task_id = self._config.task_name
        progress_file = get_tasks_dir() / f"{task_id}_progress.json"

        if progress_file.exists():
            try:
                with open(progress_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._resume_page = data.get("current_page", 0) + 1  # 下一页
                self._resume_count = data.get("current_count", 0)
            except (json.JSONDecodeError, OSError):
                self._resume_page = 0
                self._resume_count = 0

    def _log_message(self, message: str) -> None:
        """发送日志信号"""
        logger.info(message)
        self.log.emit(message)

    def _emit_error(self, message: str) -> None:
        """发送错误信号"""
        logger.error(message)
        self.error.emit(message)

    def _calculate_speed(self, count: int) -> str:
        """计算爬取速度（条/分钟）"""
        elapsed = time.time() - self._start_time
        if elapsed < 1:
            return ""
        rate = count / (elapsed / 60)
        return f"{rate:.0f}条/分钟" if rate > 1 else f"{rate*60:.0f}条/小时"

    def _calculate_eta(self, current: int, target: int) -> str:
        """计算预计剩余时间"""
        if current <= 0 or not target or target <= 0:
            return ""
        elapsed = time.time() - self._start_time
        if elapsed < 5:
            return "计算中..."
        rate = current / elapsed  # 条/秒
        remaining = (target - current) / rate if rate > 0 else 0
        if remaining < 60:
            return f"约{remaining:.0f}秒"
        elif remaining < 3600:
            return f"约{remaining/60:.0f}分钟"
        else:
            return f"约{remaining/3600:.1f}小时"
