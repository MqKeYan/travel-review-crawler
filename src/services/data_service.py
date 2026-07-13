"""
模块名称：数据查询服务

功能说明：
    - 管理爬取到的评论数据（内存缓存）
    - 支持分页查询、排序、统计
    - 线程安全（多线程读写保护）
"""

import threading
from typing import Optional

from src.models.review import ReviewStats, PageResult


class DataService:
    """
    数据查询服务。

    爬取任务完成后，评论数据暂存在此服务的内存中。
    UI 层通过此服务查询和预览数据。
    """

    def __init__(self):
        # 评论数据缓存：task_name → list[dict]
        self._data: dict[str, list[dict]] = {}

        # 已导出标记：task_name 集合
        self._exported: set[str] = set()

        # 线程锁
        self._lock = threading.RLock()

    def add_reviews(self, task_name: str, reviews: list[dict]) -> None:
        """
        添加评论数据到缓存。

        Args:
            task_name: 任务名称
            reviews: 评论数据列表
        """
        with self._lock:
            if task_name in self._data:
                self._data[task_name].extend(reviews)
            else:
                self._data[task_name] = reviews
            # 新数据写入后清除已导出标记
            self._exported.discard(task_name)

    def get_reviews(
        self,
        task_name: str,
        page: int = 1,
        size: int = 50,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> PageResult:
        """
        分页查询评论数据。

        Args:
            task_name: 任务名称
            page: 当前页码（从 1 开始）
            size: 每页条数
            sort_by: 排序字段（"time" / "rating"），None 不排序
            sort_order: 排序方向 "asc" / "desc"

        Returns:
            PageResult 分页结果
        """
        with self._lock:
            reviews = list(self._data.get(task_name, []))

        total = len(reviews)

        # 排序
        if sort_by and sort_by in ("time", "rating"):
            reverse = sort_order == "desc"
            try:
                reviews.sort(key=lambda r: (r.get(sort_by) or ""), reverse=reverse)
            except TypeError:
                # 字段类型不一致时忽略排序错误
                pass

        # 分页
        start = (page - 1) * size
        end = start + size
        page_items = reviews[start:end]

        return PageResult(
            items=page_items,
            total=total,
            page=page,
            total_pages=(total + size - 1) // size if total > 0 else 1,
            size=size,
        )

    def get_stats(self, task_name: str) -> ReviewStats:
        """
        获取任务的数据统计信息。

        Args:
            task_name: 任务名称

        Returns:
            ReviewStats 统计结果
        """
        with self._lock:
            reviews = list(self._data.get(task_name, []))

        if not reviews:
            return ReviewStats()

        total = len(reviews)
        total_rating = 0
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        times = []

        for r in reviews:
            rating = r.get("rating", 0)
            try:
                rating_int = int(rating)
                if 1 <= rating_int <= 5:
                    rating_dist[rating_int] += 1
                    total_rating += rating_int
            except (ValueError, TypeError):
                pass

            t = r.get("time", "")
            if t:
                times.append(t)

        avg_rating = total_rating / total if total > 0 else 0
        date_range = (min(times) if times else None, max(times) if times else None)

        return ReviewStats(
            total=total,
            avg_rating=round(avg_rating, 1),
            rating_distribution=rating_dist,
            date_range=date_range,
        )

    def clear_data(self, task_name: str) -> bool:
        """
        清空指定任务的评论数据。

        Args:
            task_name: 任务名称

        Returns:
            True 表示清除成功
        """
        with self._lock:
            if task_name in self._data:
                del self._data[task_name]
                return True
            return False

    def clear_all(self) -> None:
        """清空所有任务的评论数据。"""
        with self._lock:
            self._data.clear()

    def mark_exported(self, task_name: str) -> None:
        """标记任务数据已导出"""
        with self._lock:
            self._exported.add(task_name)

    def get_unexported_tasks(self) -> list[str]:
        """获取有数据但尚未导出的任务名称列表"""
        with self._lock:
            return [n for n in self._data if n not in self._exported]

    def get_all_tasks_with_data(self) -> list[str]:
        """获取所有有缓存数据的任务名称列表"""
        with self._lock:
            return list(self._data.keys())
