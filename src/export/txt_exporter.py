"""
模块名称：TXT 格式导出器

功能说明：
    - 将评论数据导出为纯文本格式
    - 每条评论包含序号、评分、用户名、时间、内容
    - UTF-8 编码，适合直接阅读和文本分析

格式示例：
    ===== 黄山风景区评论 =====
    爬取时间: 2026-06-13 10:30
    数据来源: 携程
    共 200 条评论

    【1】★★★★★ | 用户:张三 | 2024-10-15
    景色非常壮观，云海太美了！
"""

import os

import datetime

from src.export.base import BaseExporter
from src.utils.exceptions import ExportError


class TxtExporter(BaseExporter):
    """TXT 纯文本导出器"""

    format_name: str = "txt"
    file_extension: str = "txt"

    def export(
        self,
        reviews: list[dict],
        filepath: str,
        fields: list[str] | None = None,
    ) -> str:
        """
        导出为 TXT 纯文本文件。

        格式说明：
        - 文件头：名称、时间、来源、总数
        - 每条评论：序号 + 评分（星星） + 用户名 + 时间
        - 评论内容独立一行

        Args:
            reviews: 评论数据列表
            filepath: 输出路径（不含扩展名）
            fields: 忽略（TXT 格式固定输出特定字段）

        Returns:
            写入的文件完整路径

        Raises:
            ExportError: 写入文件失败
        """
        filepath = self._ensure_extension(filepath)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                # 写入文件头
                f.write(f"===== 旅游评论数据 =====\n")
                f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"共 {len(reviews)} 条评论\n")
                f.write("=" * 50 + "\n\n")

                # 写入每条评论
                star_chars = {5: "★★★★★", 4: "★★★★☆", 3: "★★★☆☆", 2: "★★☆☆☆", 1: "★☆☆☆☆"}

                for i, review in enumerate(reviews, 1):
                    rating = review.get("rating", 0)
                    stars = star_chars.get(rating, f"{rating}分")

                    username = review.get("username", "匿名")
                    time_str = review.get("time", "")
                    content = review.get("content", "")

                    f.write(f"【{i}】{stars} | 用户:{username} | {time_str}\n")
                    f.write(f"{content}\n\n")

        except OSError as e:
            raise ExportError(f"TXT 文件写入失败: {e}") from e

        return filepath
