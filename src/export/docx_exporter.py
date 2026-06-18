"""
模块名称：DOCX 格式导出器

功能说明：
    - 将评论数据导出为 Word DOCX 格式
    - 带格式表格展示
    - 适合生成阅读性强的评论汇总报告

依赖模块：
    - python-docx (第三方)
"""

import os
import datetime

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

from src.export.base import BaseExporter
from src.models.review import STANDARD_FIELDS
from src.utils.exceptions import ExportError


class DocxExporter(BaseExporter):
    """Word DOCX 格式导出器"""

    format_name: str = "docx"
    file_extension: str = "docx"

    def export(
        self,
        reviews: list[dict],
        filepath: str,
        fields: list[str] | None = None,
    ) -> str:
        """
        导出为 DOCX 格式。

        生成包含标题、统计信息和数据表格的 Word 文档。

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

        # 确定字段和表头
        if fields:
            field_names = fields
            headers = self._get_headers(fields)
        else:
            field_names = [k for k, _ in STANDARD_FIELDS]
            headers = [v for _, v in STANDARD_FIELDS]

        try:
            doc = Document()

            # 设置默认字体为微软雅黑（支持中文）
            style = doc.styles["Normal"]
            font = style.font
            font.name = "微软雅黑"
            font.size = Pt(10)
            style.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

            # ---- 文档标题 ----
            title = doc.add_heading("旅游评论数据导出报告", level=0)
            title.alignment = 1  # 居中

            # ---- 统计信息 ----
            doc.add_paragraph(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            doc.add_paragraph(f"评论总数: {len(reviews)} 条")

            # ---- 创建数据表格 ----
            table = doc.add_table(rows=len(reviews) + 1, cols=len(headers))
            table.style = "Light Grid Accent 1"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            # 表头行
            header_cells = table.rows[0].cells
            for i, header in enumerate(headers):
                header_cells[i].text = header

            # 数据行
            for row_idx, review in enumerate(reviews):
                row_cells = table.rows[row_idx + 1].cells
                for col_idx, field in enumerate(field_names):
                    value = review.get(field, "")
                    if isinstance(value, list):
                        value = "; ".join(str(v) for v in value)
                    row_cells[col_idx].text = str(value)

            # 设置表格列宽（平均分配）
            page_width = doc.sections[0].page_width
            margin = doc.sections[0].left_margin + doc.sections[0].right_margin
            col_width = (page_width - margin) / len(headers)
            for row in table.rows:
                for cell in row.cells:
                    cell.width = col_width

            doc.save(filepath)

        except OSError as e:
            raise ExportError(f"DOCX 文件写入失败: {e}") from e
        except Exception as e:
            raise ExportError(f"DOCX 导出异常: {e}") from e

        return filepath

    def _get_headers(self, fields: list[str]) -> list[str]:
        """字段名 → 中文表头"""
        field_to_header = {k: v for k, v in STANDARD_FIELDS}
        return [field_to_header.get(f, f) for f in fields]
