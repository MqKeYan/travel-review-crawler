"""
模块名称：评论数据模型

功能说明：
    - 定义标准评论对象结构
    - 评论统计信息结构
    - 分页查询结果结构

设计原则：
    - Review 使用普通字典而非 dataclass，便于序列化和跨模块传递
    - 字段名称统一为英文，与导出模块的 field_mapping 对应
"""

from dataclasses import dataclass, field
from typing import Optional


# 标准评论对象字段列表（用于导出模块的字段选择）
STANDARD_FIELDS = [
    ("username", "用户名"),
    ("rating", "评分"),
    ("content", "评论内容"),
    ("time", "评论时间"),
    ("travel_type", "出游类型"),
    ("rating_label", "评分标签"),
    ("user_level", "用户等级"),
    ("avatar_url", "用户头像"),
    ("likes", "点赞数"),
    ("reply_count", "回复数"),
    ("sub_scores", "子评分"),
    ("merchant_reply", "商家回复"),
    ("ip_location", "IP 属地"),
    ("image_urls", "图片链接"),
]

# 标准评论对象的默认空值模板
EMPTY_REVIEW = {
    "username": "",
    "rating": 0,
    "content": "",
    "time": "",
    "travel_type": "",
    "rating_label": "",
    "user_level": "",
    "avatar_url": "",
    "likes": 0,
    "reply_count": 0,
    "sub_scores": "",
    "merchant_reply": "",
    "ip_location": "",
    "image_urls": [],
}

# 评论数据类型（类型别名，实际为字典）
Review = dict

# 评论列表类型别名
ReviewList = list[Review]


@dataclass
class ReviewStats:
    """
    评论数据统计信息。

    Attributes:
        total: 总评论数
        avg_rating: 平均评分
        rating_distribution: 评分分布 {1: count, 2: count, ...}
        date_range: 时间范围 (最早, 最晚)
        top_keywords: 高频关键词 TOP 10
    """
    total: int = 0
    avg_rating: float = 0.0
    rating_distribution: dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
    date_range: tuple[Optional[str], Optional[str]] = (None, None)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class PageResult:
    """
    分页查询结果。

    Attributes:
        items: 当前页的数据列表
        total: 总记录数
        page: 当前页码
        total_pages: 总页数
        size: 每页条数
    """
    items: list = field(default_factory=list)
    total: int = 0
    page: int = 1
    total_pages: int = 0
    size: int = 50


def make_review(**kwargs) -> Review:
    """
    创建标准评论对象。

    只保留 STANDARD_FIELDS 中定义的字段，
    缺失字段使用空值填充。

    Args:
        **kwargs: 原始字段键值对

    Returns:
        标准化后的评论对象字典

    Example:
        >>> review = make_review(username="张三", rating=5, content="非常好")
    """
    review = EMPTY_REVIEW.copy()
    valid_keys = {k for k, _ in STANDARD_FIELDS}
    for key, value in kwargs.items():
        if key in valid_keys:
            review[key] = value
    return review
