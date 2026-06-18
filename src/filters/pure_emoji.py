"""
模块名称：纯表情评论过滤器

功能说明：
    - 检测评论内容是否全为 emoji 字符
    - 评论内容去除 emoji 后为空 → 整条丢弃
    - 与 EmojiFilter 配合使用：EmojiFilter 先移除 emoji，
      本过滤器检查移除后是否为空

设计思路：
    通常 EmojiFilter 先移除 emoji，然后本过滤器检查
    处理后的内容是否为空字符串。如果为空，说明原评论全是 emoji。

    注意：emoji 正则排除过大的 Unicode 范围（如 \U000024C2-\U0001F251
    会跨越 CJK 字符区导致误伤中文），必须使用精确的小范围。
"""

import re

from src.filters.base import BaseFilter, FilterResult


# emoji 范围（与 emoji_filter.py 保持一致）
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000027BF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U000024FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002B50-\U00002B55"
    "\U00002934-\U00002935"
    "\U0000231A-\U0000231B"
    "\U000025AA-\U000025FE"
    "\U00002640-\U00002642"
    "\U00002693-\U000026FA"
    "\U00002708-\U0000276F"
    "\U0000200D"
    "\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


class PureEmojiFilter(BaseFilter):
    """
    纯表情评论过滤器。

    检查一条评论是否只包含 emoji 字符（没有有意义的文本）。
    如果是，则丢弃该评论。

    注意：此过滤器应在 EmojiFilter 之后执行。
    但即使 EmojiFilter 被禁用，本过滤器也能独立检测纯 emoji 评论。
    """

    name: str = "pure_emoji"

    def process(self, review: dict) -> FilterResult:
        """
        检查评论是否全为 emoji。

        先移除所有 emoji 字符，然后检查剩余内容。
        如果剩余内容为空（或仅为空白字符），则视为纯 emoji 评论。

        Args:
            review: 评论字典

        Returns:
            passed=False 表示该评论全为 emoji，应丢弃
        """
        content = review.get("content", "")

        # 移除 emoji 后检查是否还有实际内容
        cleaned = EMOJI_PATTERN.sub("", content).strip()

        if not cleaned:
            return FilterResult(
                passed=False,
                content=content,
                reason="评论内容全为 emoji，无有效文字",
            )

        return FilterResult(
            passed=True,
            content=content,
            reason="",
        )
