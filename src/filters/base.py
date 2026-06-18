"""
模块名称：过滤器基类与责任链

功能说明：
    - 定义 FilterResult 过滤结果数据结构
    - 定义 BaseFilter 过滤器抽象基类
    - 实现 FilterChain 责任链调度器

设计模式：责任链模式（Chain of Responsibility）
    每个过滤器独立处理一条评论，决定放行或拒绝。
    链式串联，短路执行——被拒绝的评论不再经过后续过滤器。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class FilterResult:
    """
    单条评论的过滤结果。

    Attributes:
        passed: 评论是否通过过滤（True=保留，False=丢弃）
        content: 处理后的评论内容（可能被移除了图片/emoji）
        reason: 未通过时的原因描述，用于日志和用户提示
    """
    passed: bool = True
    content: str = ""
    reason: str = ""


class BaseFilter(ABC):
    """
    过滤器抽象基类。

    所有内容过滤器必须继承此类，并实现 process() 方法。
    __call__ 方法使过滤器实例可以像函数一样调用，
    并且在过滤器被禁用时自动放行。

    Attributes:
        name: 过滤器名称（用于日志标识和用户配置）
        enabled: 是否启用（由用户配置控制）
    """

    name: str = "base"
    enabled: bool = True

    def __init__(self, enabled: bool = True):
        """
        初始化过滤器。

        Args:
            enabled: 是否启用
        """
        self.enabled = enabled

    @abstractmethod
    def process(self, review: dict) -> FilterResult:
        """
        处理单条评论。

        子类必须实现此方法，返回 FilterResult 说明处理结果。

        Args:
            review: 标准评论对象字典，至少包含 "content" 字段

        Returns:
            FilterResult 包含是否通过、处理后内容、拒绝原因
        """
        ...

    def __call__(self, review: dict) -> FilterResult:
        """
        使过滤器实例可调用。

        如果过滤器被禁用，直接放行并保持内容不变。
        否则调用 process() 执行实际过滤逻辑。

        Args:
            review: 标准评论对象字典

        Returns:
            过滤结果
        """
        if not self.enabled:
            return FilterResult(passed=True, content=review.get("content", ""))
        return self.process(review)


class FilterChain:
    """
    过滤器责任链。

    按注册顺序依次执行所有过滤器。
    某条评论被任一过滤器拒绝后，不再执行后续过滤器（短路优化）。
    被拒绝的评论会被记录到 rejected 列表，并注明由哪个过滤器拒绝。
    """

    def __init__(self):
        self._filters: list[BaseFilter] = []

    def add_filter(self, filter_: BaseFilter) -> "FilterChain":
        """
        添加过滤器到链尾。

        Args:
            filter_: 过滤器实例

        Returns:
            self，支持链式调用
        """
        self._filters.append(filter_)
        return self

    @property
    def filters(self) -> list[BaseFilter]:
        """获取当前链上的所有过滤器"""
        return list(self._filters)

    def apply(self, reviews: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        对评论列表依次执行所有过滤器。

        Args:
            reviews: 原始评论列表

        Returns:
            (passed, rejected) 元组：
            - passed: 通过所有过滤器的评论列表
            - rejected: 被拒绝的评论列表（每条额外包含 _filter 和 _reason 字段）
        """
        passed: list[dict] = []
        rejected: list[dict] = []

        for review in reviews:
            original_content = review.get("content", "")
            is_ok = True

            for f in self._filters:
                result = f(review)
                if not result.passed:
                    rejected.append({
                        **review,
                        "_filter": f.name,
                        "_reason": result.reason,
                    })
                    is_ok = False
                    break  # 短路：不再执行后续过滤器
                # 将处理后的内容写回评论对象，供后续过滤器和导出使用
                review["content"] = result.content

            if is_ok:
                passed.append(review)

        return passed, rejected
