"""
模块名称：CSV 格式导出器

功能说明：
    - 将评论数据导出为 CSV（逗号分隔值）格式
    - UTF-8 BOM 编码，确保 Excel 直接打开不乱码
    - 支持自定义字段选择
    - 自动处理字段值中的逗号和引号
"""

import csv
import os

from src.export.base import BaseExporter
from src.models.review import STANDARD_FIELDS
from src.utils.exceptions import ExportError


class CsvExporter(BaseExporter):
    """CSV 逗号分隔值导出器"""

    format_name: str = "csv"
    file_extension: str = "csv"

    def export(
        self,
        reviews: list[dict],
        filepath: str,
        fields: list[str] | None = None,
    ) -> str:
        """
        导出为 CSV 格式。

        使用 UTF-8 BOM 编码，Excel 可直接打开显示中文。
        字段值中的逗号、换行符、引号会被自动转义。

        Args:
            reviews: 评论数据列表
            filepath: 输出路径（不含扩展名）
            fields: 需要导出的字段列，None 则导出所有标准字段

        Returns:
            写入的文件完整路径

        Raises:
            ExportError: 写入文件失败
        """
        filepath = self._ensure_extension(filepath)

        # 确定导出的字段和表头
        if fields:
            field_names = fields
            headers = []
            for f in fields:
                # 从 STANDARD_FIELDS 查找中文表头
                label = f
                for key, display in STANDARD_FIELDS:
                    if key == f:
                        label = display
                        break
                headers.append(label)
        else:
            field_names = [k for k, _ in STANDARD_FIELDS]
            headers = [v for _, v in STANDARD_FIELDS]

        try:
            with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

                for review in reviews:
                    row = []
                    for field in field_names:
                        value = review.get(field, "")
                        if isinstance(value, list):
                            value = "; ".join(str(v) for v in value)
                        row.append(value)
                    writer.writerow(row)

        except OSError as e:
            raise ExportError(f"CSV 文件写入失败: {e}") from e

        return filepath
