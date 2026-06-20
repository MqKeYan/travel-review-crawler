"""
模块名称：网站适配器基类

功能说明：
    - 定义网站适配器的基类和数据结构
    - 提供 HTML 页面解析函数（BeautifulSoup + CSS 选择器）
    - 字段映射：将各网站原始字段统一转换为标准评论字段

设计原则：
    - 声明式配置：子类只需填充字段，无需编写解析逻辑
    - HTML 解析：通过 raw_html_parser / custom_extractor / CSS 选择器提取评论
    - 统一输出：所有网站输出标准评论对象，后续处理与具体网站解耦
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HttpMethod(Enum):
    """HTTP 请求方法枚举"""
    GET = "GET"
    POST = "POST"


@dataclass
class SiteAdapter:
    """
    网站适配器基类。

    每个目标网站创建一个适配器实例，配置该网站特有的请求参数和解析规则。
    适配器只包含配置数据，不包含业务逻辑——解析逻辑统一由基类的 parse_response 实现。

    Attributes:
        site_name: 网站标识（如 "ctrip"、"dianping"）
        site_display_name: 用户可见的显示名称（如 "携程"）
        domain: 网站 Cookie 域名（如 ".ctrip.com"）
        login_url: 登录页 URL（用于自动拉起浏览器）

        http_method: HTTP 方法（GET / POST）

        page_size: 每页评论条数
        page_start: 起始页码（通常为 1 或 0）
        max_pages_limit: 单次任务最大翻页数（安全上限，默认 100）

        field_mapping: 网站原始字段名 → 标准评论对象字段名

        review_selector: HTML 模式下单条评论的 CSS 选择器
        review_list_selector: HTML 模式下评论列表容器的 CSS 选择器
    """

    # === 基础信息 ===
    site_name: str = ""
    site_display_name: str = ""
    domain: str = ""
    login_url: str = ""
    url_template: str = ""  # 从ID构造URL的模板，如 "https://www.dianping.com/shop/{id}"

    # === 请求参数 ===
    http_method: HttpMethod = HttpMethod.GET

    # === 分页参数 ===
    page_size: int = 20
    page_start: int = 1
    max_pages_limit: int = 100

    # === 字段映射：网站原始字段 → 标准字段 ===
    field_mapping: dict = field(default_factory=lambda: {
        "userName": "username",
        "commentContent": "content",
        "commentScore": "rating",
        "commentTime": "time",
        "userLevel": "user_level",
        "likeCount": "likes",
        "replyCount": "reply_count",
        "travelType": "travel_type",
        "merchantReply": "merchant_reply",
        "ipLocation": "ip_location",
        "imageUrls": "image_urls",
    })

    # === HTML 解析：CSS 选择器 ===
    review_selector: str = ""
    review_list_selector: str = ""
    # 自定义单元素提取函数 (soup_item) -> dict
    custom_extractor: callable = None
    # 自定义原始 HTML 解析器 (response_text) -> list[dict]
    # 当需要从嵌入式 JSON 等非标签结构提取时使用（优先级最高）
    raw_html_parser: callable = None
    # Selenium 翻页爬虫 (url, max_pages, max_count, timeout, stop_check) -> list[dict]
    # 当 HTML 页面需要 JS 渲染翻页时使用
    selenium_crawler: callable = None


def parse_response(response, adapter: SiteAdapter) -> list[dict]:
    """
    HTML 页面解析。

    解析步骤：
    1. 如果设置了 raw_html_parser，直接调用它处理全文
    2. 否则用 BeautifulSoup + CSS 选择器定位评论容器
    3. 如果设置了 custom_extractor，用自定义函数提取每个容器
    4. 否则使用默认的 _extract_item 纯文本提取

    Args:
        response: requests.Response 对象
        adapter: 网站适配器实例

    Returns:
        标准格式的评论列表
    """
    # 优先级1：自定义全文解析器（如从嵌入式 JSON 提取）
    if adapter.raw_html_parser:
        return adapter.raw_html_parser(response.text)

    # 优先级2：CSS 选择器定位 + 元素提取
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "lxml")

    if adapter.review_selector:
        items = soup.select(adapter.review_selector)
    else:
        items = []

    if adapter.custom_extractor:
        return [adapter.custom_extractor(item) for item in items]
    return [_extract_item(item) for item in items]


def _extract_item(item) -> dict:
    """
    从单个 HTML 元素中提取评论字段（默认纯文本提取）。

    Args:
        item: BeautifulSoup Tag 对象

    Returns:
        标准评论字典
    """
    content = item.get_text(strip=True) if hasattr(item, "get_text") else str(item)

    return {
        "username": "",
        "rating": 0,
        "content": content,
        "time": "",
        "user_level": "",
        "likes": 0,
        "reply_count": 0,
        "travel_type": "",
        "merchant_reply": "",
        "ip_location": "",
        "image_urls": [],
    }


def _get_nested_value(data: dict, path: str):
    """
    按点号分隔的路径从嵌套字典中取值（保留供 Ctrip 等嵌入式 JSON 解析使用）。

    Example:
        >>> data = {"result": {"data": {"items": [1, 2]}}}
        >>> _get_nested_value(data, "result.data.items")
        [1, 2]
    """
    keys = path.split(".")
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        elif isinstance(result, list) and key.lstrip("-").isdigit():
            try:
                result = result[int(key)]
            except (IndexError, ValueError):
                return None
        else:
            return None
    return result


def extract_resource_id(url: str) -> str | None:
    """
    从携程 URL 中提取景点/产品的数字 ID。

    支持多种 URL 格式：
    - you.ctrip.com/sight/xxx/521.html     → 521
    - m.ctrip.com/webapp/you/sight/521/... → 521
    - vacations.ctrip.com/travel/detail/p1234567 → 1234567
    - 兜底：取 URL 中最后一串 ≥4 位的连续数字
    """
    import re

    m = re.search(r'/sight/[^/]+/(\d+)', url)
    if m:
        return m.group(1)

    m = re.search(r'/sight/(\d+)(?:/|\.html)', url)
    if m:
        return m.group(1)

    m = re.search(r'/p(\d{5,})(?:\.html)?', url)
    if m:
        return m.group(1)

    m = re.search(r'/(\d{4,})(?:\.html|/)', url)
    if m:
        return m.group(1)

    return None


def _apply_field_mapping(item: dict, mapping: dict) -> dict:
    """
    将原始字段名映射为标准字段名（保留供站点内部使用）。

    Args:
        item: 原始评论数据字典
        mapping: 字段映射表 {原始字段名: 标准字段名}

    Returns:
        字段已映射的标准评论字典
    """
    review = {
        "username": "",
        "rating": 0,
        "content": "",
        "time": "",
        "user_level": "",
        "likes": 0,
        "reply_count": 0,
        "travel_type": "",
        "merchant_reply": "",
        "ip_location": "",
        "image_urls": [],
    }

    for raw_key, standard_key in mapping.items():
        if raw_key in item:
            review[standard_key] = item[raw_key]

    return review
