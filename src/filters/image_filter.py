"""
模块名称：图片过滤器

功能说明：
    - 移除评论内容中的 HTML <img> 标签
    - 移除评论内容中的图片链接（http...jpg/png/gif 等）
    - 保留非图片链接的其他文本内容

正则说明：
    - <img[^>]*> : 匹配 HTML img 标签及其全部属性
    - https?://[^\\s]+\\.(jpg|jpeg|png|gif|bmp|webp) : 匹配常见图片格式 URL
"""

import re

from src.filters.base import BaseFilter, FilterResult


# HTML <img> 标签正则
IMG_TAG_PATTERN = re.compile(r"<img[^>]*>", re.IGNORECASE)

# 图片 URL 正则（常见图片扩展名）
IMG_URL_PATTERN = re.compile(
    r"https?://[^\s]+\.(jpg|jpeg|png|gif|bmp|webp|svg)(\?[^\s]*)?",
    re.IGNORECASE,
)


class ImageFilter(BaseFilter):
    """
    图片过滤器。

    移除评论中的 HTML 图片标签和纯文本图片链接。
    只移除图片标记本身，评论的其他文字内容保留。
    """

    name: str = "image"

    def process(self, review: dict) -> FilterResult:
        """
        移除评论中的图片标签和图片链接。

        先移除 HTML 的 <img> 标签（如果有），
        再移除纯文本中的图片 URL。

        Args:
            review: 评论字典

        Returns:
            处理后的结果
        """
        content = review.get("content", "")

        # 第一步：移除 HTML <img> 标签
        content = IMG_TAG_PATTERN.sub("", content)

        # 第二步：移除图片 URL（替换为空字符串而不是标记"[图片]"，保持干净）
        content = IMG_URL_PATTERN.sub("", content)

        # 清理多余空格
        content = re.sub(r"\s+", " ", content).strip()

        return FilterResult(
            passed=True,
            content=content,
            reason="",
        )
