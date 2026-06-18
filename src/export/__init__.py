"""
导出引擎包，提供多种格式的数据导出功能。

支持的导出格式：TXT、CSV、XLSX、DOCX

入口函数：
    export_reviews(reviews, format, filepath, fields) -> str
    get_exporter(format_name) -> BaseExporter | None
"""

from src.export.base import BaseExporter
from src.export.txt_exporter import TxtExporter
from src.export.csv_exporter import CsvExporter
from src.export.xlsx_exporter import XlsxExporter
from src.export.docx_exporter import DocxExporter

from src.utils.exceptions import ExportFormatError

# 导出器注册表：格式名 → 导出器类
_EXPORTER_REGISTRY: dict[str, type[BaseExporter]] = {
    "txt": TxtExporter,
    "csv": CsvExporter,
    "xlsx": XlsxExporter,
    "docx": DocxExporter,
}


def get_exporter(format_name: str) -> BaseExporter:
    """
    根据格式名称获取导出器实例。

    Args:
        format_name: 格式名称（"txt" / "csv" / "xlsx" / "docx"）

    Returns:
        导出器实例

    Raises:
        ExportFormatError: 不支持的导出格式
    """
    exporter_class = _EXPORTER_REGISTRY.get(format_name.lower())
    if exporter_class is None:
        raise ExportFormatError(f"不支持的导出格式: {format_name}")
    return exporter_class()


def export_reviews(
    reviews: list[dict],
    format_name: str,
    filepath: str,
    fields: list[str] | None = None,
) -> str:
    """
    将评论数据导出为指定格式的文件。

    便捷函数，直接调用无需先获取导出器实例。

    Args:
        reviews: 标准评论对象列表
        format_name: 导出格式（"txt" / "csv" / "xlsx" / "docx"）
        filepath: 输出文件路径（不含扩展名）
        fields: 需要导出的字段名列表，None 表示全部

    Returns:
        实际写入的文件完整路径

    Example:
        >>> path = export_reviews(reviews, "xlsx", "/path/to/output")
        >>> print(f"已导出到: {path}")
    """
    exporter = get_exporter(format_name)
    return exporter.export(reviews, filepath, fields)


__all__ = [
    "BaseExporter",
    "TxtExporter", "CsvExporter", "XlsxExporter", "DocxExporter",
    "get_exporter", "export_reviews",
]
