"""
模块名称：关键词/广告过滤器

功能说明：
    - 敏感词黑名单匹配（用户可配置）
    - 广告特征词匹配（内置广告关键词库）
    - 支持两种处理方式：标记（mark）或丢弃（discard）

匹配策略：子串匹配（不区分大小写和白空格）
    例如敏感词 "加微信" 可以匹配 "加 微信"、"加我微信" 等变体。
"""

import re

from src.filters.base import BaseFilter, FilterResult


# 内置广告特征词库
# 这些是常见的旅游评论中的广告/引流关键词
DEFAULT_AD_KEYWORDS = [
    "加微信",
    "加V",
    "扫码",
    "免费领",
    "抽奖",
    "中奖",
    "优惠券",
    "内部价",
    "特价票",
    "代购",
    "代订",
    "转发",
    "集赞",
    "点赞有礼",
    "红包",
    "返现",
    "好评返现",
    "刷单",
    "兼职",
]


class KeywordFilter(BaseFilter):
    """
    关键词/广告过滤器。

    支持两种关键词来源：
    1. 用户自定义的敏感词列表
    2. 内置广告特征词库

    两种处理方式：
    - mark: 命中关键词的评论被标记（添加 _keyword_hit 字段），仍保留
    - discard: 命中关键词的评论被丢弃
    """

    name: str = "keyword"

    def __init__(
        self,
        enabled: bool = True,
        sensitive_words: list[str] | None = None,
        ad_filter: bool = True,
        action: str = "discard",
    ):
        """
        初始化关键词过滤器。

        Args:
            enabled: 是否启用
            sensitive_words: 用户自定义敏感词列表
            ad_filter: 是否启用广告特征词过滤
            action: "mark" 标记 / "discard" 丢弃
        """
        super().__init__(enabled=enabled)
        self.action = action

        # 合并关键词列表
        self._keywords: list[str] = list(sensitive_words or [])
        if ad_filter:
            self._keywords.extend(DEFAULT_AD_KEYWORDS)

        # 编译正则（去空白 + 不区分大小写）
        # 对每个关键词，在字符间插入 \s* 匹配可能的空格
        self._patterns: list[re.Pattern] = []
        for kw in self._keywords:
            if not kw.strip():
                continue
            # 关键词中每个字符之间允许 0 或多个空白
            pattern = r"\s*".join(re.escape(c) for c in kw.strip())
            self._patterns.append(re.compile(pattern, re.IGNORECASE))

    def process(self, review: dict) -> FilterResult:
        """
        检查评论是否包含敏感词或广告词。

        对评论内容和用户名同时检查。

        Args:
            review: 评论字典

        Returns:
            mark 模式：命中时 passed=True 但添加 _keyword_hit 字段
            discard 模式：命中时 passed=False
        """
        content = review.get("content", "")
        username = review.get("username", "")

        # 对内容和用户名进行关键词匹配
        for pattern in self._patterns:
            if pattern.search(content) or pattern.search(username):
                reason = f"命中关键词: {pattern.pattern[:30]}..."

                if self.action == "mark":
                    # 标记模式：添加字段标记，不拒绝
                    review["_keyword_hit"] = True
                    return FilterResult(passed=True, content=content, reason=reason)
                else:
                    # 丢弃模式：拒绝该评论
                    return FilterResult(passed=False, content=content, reason=reason)

        return FilterResult(passed=True, content=content, reason="")
