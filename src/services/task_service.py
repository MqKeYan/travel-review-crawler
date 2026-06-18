"""
模块名称：任务管理服务

功能说明：
    - 爬取任务的创建、启动、暂停、恢复、停止、删除
    - 任务列表查询（分页 + 筛选）
    - 任务进度跟踪
    - 使用 QThread 管理爬取工作线程
"""

import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from src.models.task import Task, TaskConfig, TaskStatus
from src.workers.crawl_worker import CrawlWorker
from src.utils.paths import get_tasks_dir
from src.sites import get_site_adapter

logger = logging.getLogger("tour-crawler.task_service")

# 进度过期天数（7 天）
_PROGRESS_EXPIRE_DAYS = 7


class TaskService:
    """
    爬取任务管理服务。

    维护任务的内存字典，管理每个任务的 CrawlWorker 线程生命周期。
    """

    def __init__(self):
        # 任务存储：task_name → Task 对象
        self._tasks: dict[str, Task] = {}

        # 工作线程：task_name → CrawlWorker
        self._workers: dict[str, CrawlWorker] = {}

        # 锁（线程安全）
        self._lock = threading.Lock()

        # 从磁盘加载已保存的任务
        self._load_from_disk()

    # ==================== 持久化 ====================

    def _task_file_path(self, task_name: str) -> Path:
        """获取任务 JSON 文件的存储路径"""
        # 移除文件名中不允许的字符
        safe_name = "".join(c for c in task_name if c.isalnum() or c in " _-")
        return get_tasks_dir() / f"{safe_name}.json"

    def _save_to_disk(self) -> None:
        """
        将所有任务保存到磁盘。

        每个任务存储为独立的 JSON 文件，包含任务信息和实时进度。
        线程安全（持有锁）。
        """
        with self._lock:
            tasks = list(self._tasks.values())
        for task in tasks:
            try:
                filepath = self._task_file_path(task.task_name)
                data = task.to_dict()
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                logger.exception(f"保存任务 [{task.task_name}] 到磁盘失败")

    def _load_from_disk(self) -> None:
        """
        从磁盘加载所有已保存的任务。

        自动清理过期进度（完成/出错超过 7 天的任务清除进度数据，
        但保留任务基本信息）。
        """
        tasks_dir = get_tasks_dir()
        if not tasks_dir.exists():
            return

        now = datetime.now()
        cutoff = now - timedelta(days=_PROGRESS_EXPIRE_DAYS)

        for filepath in sorted(tasks_dir.glob("*.json")):
            try:
                # 跳过空文件（写入中断导致的残损文件）
                if filepath.stat().st_size == 0:
                    filepath.unlink()
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                task = Task.from_dict(data)

                # ---- 7 天过期进度清理 ----
                # 如果任务已结束（完成/出错/取消），且结束时间超过 7 天，则清除进度
                if task.status in (TaskStatus.COMPLETED, TaskStatus.ERROR, TaskStatus.CANCELLED):
                    time_field = task.completed_at or task.started_at or task.created_at
                    if time_field:
                        try:
                            task_time = datetime.strptime(time_field, "%Y-%m-%d %H:%M:%S")
                            if task_time < cutoff:
                                # 清除进度，保留任务信息
                                task.progress = TaskProgress()
                                task.total_reviews = data.get("total_reviews", 0)
                        except ValueError:
                            pass

                self._tasks[task.task_name] = task

            except Exception:
                logger.exception(f"从磁盘加载任务文件失败: {filepath}")

    # ==================== 查询 ====================

    def get_tasks(
        self,
        page: int = 1,
        size: int = 50,
        status_filter: str | None = None,
    ) -> dict:
        """
        获取任务列表（分页 + 可选状态筛选）。

        Args:
            page: 当前页码
            size: 每页条数
            status_filter: 状态筛选（"running"/"completed"/"pending"/None=全部）

        Returns:
            分页结果字典，包含 items、total、page、total_pages
        """
        with self._lock:
            tasks = list(self._tasks.values())

        if status_filter:
            tasks = [t for t in tasks if t.status.value == status_filter]

        # 按创建时间降序排列
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        total = len(tasks)
        start = (page - 1) * size
        end = start + size
        page_items = tasks[start:end]

        return {
            "items": [t.to_dict() for t in page_items],
            "total": total,
            "page": page,
            "total_pages": (total + size - 1) // size if total > 0 else 1,
        }

    def create_task(self, config: TaskConfig) -> Task:
        """
        创建新爬取任务。

        Args:
            config: 任务配置

        Returns:
            创建后的 Task 对象
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        # 获取网站中文名
        adapter = get_site_adapter(config.site)
        site_display_name = adapter.site_display_name if adapter else config.site

        task = Task(
            task_name=config.task_name,
            task_id=config.task_name,  # 简单起见，用任务名做标识
            site=config.site,
            site_display_name=site_display_name,
            target_url=config.target_url,
            status=TaskStatus.PENDING,
            config=config,
            created_at=now,
        )

        with self._lock:
            self._tasks[task.task_name] = task

        logger.info(f"创建任务 [{task.task_name}]: {config.site}-{config.task_name}")
        self._save_to_disk()
        return task

    def get_task(self, task_name: str) -> Task | None:
        """
        获取任务详情。

        Args:
            task_name: 任务名称

        Returns:
            Task 对象，不存在返回 None
        """
        with self._lock:
            return self._tasks.get(task_name)

    def start_task(self, task_name: str) -> CrawlWorker | None:
        """
        准备启动任务（创建爬取工作线程但不启动）。

        由调用方在连接 Signal 后调用 worker.start()。

        Args:
            task_name: 任务名称

        Returns:
            CrawlWorker 实例，启动失败返回 None
        """
        with self._lock:
            task = self._tasks.get(task_name)
            if task is None:
                logger.warning(f"任务不存在: {task_name}")
                return None

            if task.status in (TaskStatus.RUNNING, TaskStatus.COMPLETED):
                logger.warning(f"任务状态不允许启动: {task.status.value}")
                return None

            # 创建工作线程（不启动，由调用方启动）
            worker = CrawlWorker(task.config)
            self._workers[task_name] = worker

            task.status = TaskStatus.RUNNING
            task.started_at = time.strftime("%Y-%m-%d %H:%M:%S")

        self._save_to_disk()
        logger.info(f"任务 [{task_name}] 已准备启动")
        return worker

    def pause_task(self, task_name: str) -> bool:
        """
        暂停运行中的任务。

        Args:
            task_name: 任务名称

        Returns:
            True 表示暂停成功
        """
        with self._lock:
            worker = self._workers.get(task_name)
            task = self._tasks.get(task_name)

        if worker and task:
            worker.pause()
            task.status = TaskStatus.PAUSED
            self._save_to_disk()
            logger.info(f"任务 [{task_name}] 已暂停")
            return True
        return False

    def resume_task(self, task_name: str) -> bool:
        """
        恢复暂停的任务。

        Args:
            task_name: 任务名称

        Returns:
            True 表示恢复成功
        """
        with self._lock:
            worker = self._workers.get(task_name)
            task = self._tasks.get(task_name)

        if worker and task:
            worker.resume()
            task.status = TaskStatus.RUNNING
            self._save_to_disk()
            logger.info(f"任务 [{task_name}] 已恢复")
            return True
        return False

    def stop_task(self, task_name: str, complete_early: bool = False) -> bool:
        """
        停止运行中或暂停的任务。

        不阻塞主线程：仅设置停止标志，线程自行退出后由 complete/error 信号处理收尾。

        Args:
            task_name: 任务名称
            complete_early: True 则标记为已完成（保留已爬数据），False 标记为已取消

        Returns:
            True 表示停止信号已发送
        """
        with self._lock:
            worker = self._workers.get(task_name)
            task = self._tasks.get(task_name)

        if worker:
            worker.stop()

        if task:
            task.status = TaskStatus.COMPLETED if complete_early else TaskStatus.CANCELLED
            task.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")

        self._save_to_disk()
        logger.info(f"任务 [{task_name}] {'已提前完成' if complete_early else '已停止'}")
        return True

    def delete_task(self, task_name: str) -> bool:
        """
        删除任务及其爬取数据。

        先停止任务（如果正在运行），再清除内存中的数据。

        Args:
            task_name: 任务名称

        Returns:
            True 表示删除成功
        """
        self.stop_task(task_name)

        with self._lock:
            self._tasks.pop(task_name, None)

        # 删除磁盘上的任务文件
        try:
            filepath = self._task_file_path(task_name)
            if filepath.exists():
                filepath.unlink()
        except Exception:
            logger.exception(f"删除任务文件失败: {task_name}")

        logger.info(f"任务 [{task_name}] 已删除")
        return True

    def get_worker(self, task_name: str) -> CrawlWorker | None:
        """
        获取任务的工作线程实例（用于连接 Signal）。

        Args:
            task_name: 任务名称

        Returns:
            CrawlWorker 实例，不存在返回 None
        """
        return self._workers.get(task_name)
