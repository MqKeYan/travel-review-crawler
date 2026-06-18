"""
模块名称：导出器基类

功能说明：
    - 定义所有导出器的抽象基类
    - 统一导出接口规范
    - 提供文件路径自动完成功能（追加扩展名）

设计原则：
    - 所有导出器继承同一接口，便于扩展新格式
    - 导出器只负责格式转换和文件写入，不参与业务逻辑
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseExporter(ABC):
    """
    导出器抽象基类。

    子类必须覆写 format_name、file_extension 和 export() 方法。

    Attributes:
        format_name: 格式名称（如 "xlsx"），用于标识和注册
        file_extension: 文件扩展名（如 ".xlsx"），不含点号
    """

    format_name: str = ""
    file_extension: str = ""

    @abstractmethod
    def export(
        self,
        reviews: list[dict],
        filepath: str,
        fields: list[str] | None = None,
    ) -> str:
        """
        将评论数据导出为文件。

        Args:
            reviews: 标准评论对象列表
            filepath: 输出文件路径（不含扩展名，方法内部自动追加）
            fields: 需要导出的字段名列表，None 表示导出全部可用字段

        Returns:
            实际写入的文件完整路径

        Raises:
            ExportError: 导出过程中发生错误
            ExportPermissionError: 文件写入权限不足
        """
        ...

    def _ensure_extension(self, filepath: str) -> str:
        """
        确保文件路径包含正确的扩展名。

        如果 filepath 已有扩展名且与当前导出器匹配，不做修改。
        否则自动追加扩展名。

        Args:
            filepath: 原始文件路径

        Returns:
            确保有正确扩展名的文件路径
        """
        if not filepath.endswith(f".{self.file_extension}"):
            return f"{filepath}.{self.file_extension}"
        return filepath

    def _filter_fields(self, review: dict, fields: list[str] | None) -> dict:
        """
        根据字段列表过滤评论对象的键。

        Args:
            review: 评论字典
            fields: 需要保留的字段列表

        Returns:
            过滤后的评论字典（仅包含指定字段）
        """
        if fields is None:
            return review
        return {k: review.get(k, "") for k in fields}
