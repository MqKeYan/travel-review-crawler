"""
过滤器包，提供评论内容过滤功能。

使用责任链模式：多个过滤器按顺序串联执行，
任一过滤器拒绝某条评论时，不再执行后续过滤器（短路）。

入口函数：
    build_filter_chain(config: FilterConfig) -> FilterChain
"""

from src.filters.base import BaseFilter, FilterResult, FilterChain
from src.filters.emoji_filter import EmojiFilter
from src.filters.image_filter import ImageFilter
from src.filters.keyword_filter import KeywordFilter
from src.filters.pure_emoji import PureEmojiFilter
from src.models.task import FilterConfig


def build_filter_chain(config: FilterConfig) -> FilterChain:
    """
    根据配置构建过滤器责任链。

    按顺序注册：
    1. 图片过滤器 → 2. emoji 过滤器
    → 3. 纯表情过滤器 → 4. 关键词过滤器

    Args:
        config: 过滤配置

    Returns:
        配置好的过滤器链
    """
    chain = FilterChain()

    # 图片过滤器（移除 <img> 标签和图片链接）
    chain.add_filter(ImageFilter(enabled=config.remove_images))

    # Emoji 过滤器（移除 emoji 字符）
    chain.add_filter(EmojiFilter(enabled=config.remove_emoji))

    # 纯表情过滤器（跳过纯 emoji 评论）
    chain.add_filter(PureEmojiFilter(enabled=config.skip_pure_emoji))

    # 关键词/广告过滤器
    chain.add_filter(KeywordFilter(
        enabled=config.ad_filter or bool(config.sensitive_words),
        sensitive_words=config.sensitive_words,
        ad_filter=config.ad_filter,
        action=config.filter_action,
    ))

    return chain


__all__ = [
    "BaseFilter", "FilterResult", "FilterChain",
    "EmojiFilter", "ImageFilter", "KeywordFilter", "PureEmojiFilter",
    "build_filter_chain",
]
