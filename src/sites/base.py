"""
模块名称：网站适配器基类

功能说明：
    - 定义网站适配器的基类和数据结构
    - 提供通用解析函数（HTML/CSS 选择器 + JSON API 双路径）
    - 字段映射：将各网站原始字段统一转换为标准评论字段

设计原则：
    - 声明式配置：子类只需填充字段，无需编写解析逻辑
    - 双路径解析：request_type 决定走 HTML 路径还是 JSON 路径
    - 统一输出：所有网站输出标准评论对象，后续处理与具体网站解耦
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RequestType(Enum):
    """
    请求类型枚举。

    HTML: 网站返回 HTML 页面，使用 BeautifulSoup + CSS 选择器解析
    JSON_API: 网站提供 JSON 接口，直接解析 JSON 响应
    """
    HTML = "html"
    JSON_API = "json_api"


class HttpMethod(Enum):
    """HTTP 请求方法枚举"""
    GET = "GET"
    POST = "POST"


@dataclass
class SiteAdapter:
    """
    网站适配器基类。

    每个目标网站创建一个适配器类，继承此类并覆写对应字段。
    适配器只包含配置数据，不包含业务逻辑——解析逻辑统一由基类的 parse_response 实现。

    Attributes:
        site_name: 网站标识（如 "ctrip"、"meituan"）
        site_display_name: 用户可见的显示名称（如 "携程"）
        domain: 网站 Cookie 域名（如 ".ctrip.com"）
        login_url: 登录页 URL（用于自动拉起浏览器）

        request_type: 请求类型（HTML / JSON_API）
        http_method: HTTP 方法（GET / POST）
        api_endpoint: 评论数据接口 URL（JSON API 模式必填）
        api_params_template: URL 参数模板，{page} 占位符
        api_body_template: POST 请求体模板

        page_param_name: 翻页参数名（默认 "page"）
        page_size: 每页评论条数
        page_start: 起始页码（通常为 1 或 0）
        max_pages_limit: 单次任务最大翻页数（安全上限，默认 100）

        field_mapping: 网站原始字段名 → 标准评论对象字段名

        review_selector: HTML 模式下单条评论的 CSS 选择器
        review_list_selector: HTML 模式下评论列表容器的 CSS 选择器
        next_page_selector: HTML 模式下下一页按钮的 CSS 选择器

        reviews_json_path: JSON 模式下评论列表的 JSON 路径
        total_count_json_path: JSON 模式下总条数的 JSON 路径
    """

    # === 基础信息 ===
    site_name: str = ""
    site_display_name: str = ""
    domain: str = ""
    login_url: str = ""

    # === 请求参数 ===
    request_type: RequestType = RequestType.HTML
    http_method: HttpMethod = HttpMethod.GET
    api_endpoint: str = ""
    api_params_template: dict = field(default_factory=dict)
    api_body_template: dict = field(default_factory=dict)

    # === 分页参数 ===
    page_param_name: str = "page"
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
    next_page_selector: str = ""
    # 自定义单元素提取函数 (soup_item) -> dict
    # 当每个评论有固定 HTML 结构时，用此代替默认的 _extract_item
    custom_extractor: callable = None
    # 自定义原始 HTML 解析器 (response_text) -> list[dict]
    # 当需要从嵌入式 JSON 等非标签结构提取时使用（优先级最高）
    raw_html_parser: callable = None
    # Selenium 翻页爬虫 (url, max_pages, max_count, timeout, stop_check) -> list[dict]
    # 当 HTML 页面需要 JS 渲染翻页时使用
    selenium_crawler: callable = None

    # === JSON API 解析：JSON 路径 ===
    reviews_json_path: str = ""
    total_count_json_path: str = ""


def parse_response(response, adapter: SiteAdapter) -> list[dict]:
    """
    根据适配器的 request_type 自动选择解析方式。

    此函数是爬虫引擎和网站适配层之间的核心桥梁，
    它将原始 HTTP 响应统一转换为标准的评论对象列表。

    Args:
        response: requests.Response 对象
        adapter: 网站适配器实例

    Returns:
        标准格式的评论列表，每个元素为字段统一的评论字典

    Raises:
        ValueError: 未知的 request_type
    """
    if adapter.request_type == RequestType.JSON_API:
        return _parse_json_api(response, adapter)
    elif adapter.request_type == RequestType.HTML:
        return _parse_html(response, adapter)
    else:
        raise ValueError(f"不支持的请求类型: {adapter.request_type}")


def _parse_json_api(response, adapter: SiteAdapter) -> list[dict]:
    """
    JSON API 响应解析。

    解析步骤：
    1. response.json() 获取完整 JSON 数据
    2. 按 reviews_json_path 路径提取评论列表（如 "data.list"）
    3. 通过 field_mapping 将原始字段转换为标准字段

    Args:
        response: HTTP 响应
        adapter: 网站适配器

    Returns:
        标准评论列表
    """
    data = response.json()
    # 按点号分隔路径提取嵌套数据
    if adapter.reviews_json_path:
        reviews = _get_nested_value(data, adapter.reviews_json_path) or []
    else:
        reviews = data.get("list", data.get("data", data.get("comments", [])))
        # 确保 reviews 是列表
        if isinstance(reviews, dict):
            reviews = list(reviews.values())

    if not isinstance(reviews, list):
        return []

    return [_apply_field_mapping(item, adapter.field_mapping) for item in reviews]


def _parse_html(response, adapter: SiteAdapter) -> list[dict]:
    """
    HTML 页面解析。

    解析步骤：
    1. 如果设置了 raw_html_parser，直接调用它处理全文
    2. 否则用 BeautifulSoup + CSS 选择器定位评论容器
    3. 如果设置了 custom_extractor，用自定义函数提取每个容器
    4. 否则使用默认的 _extract_item 纯文本提取

    Args:
        response: HTTP 响应
        adapter: 网站适配器

    Returns:
        标准评论列表
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
    return [_extract_item(item, adapter) for item in items]


def _extract_item(item, adapter: SiteAdapter) -> dict:
    """
    从单个 HTML 元素中提取评论字段。

    使用适配器的 field_mapping 反向映射：
    对于每个标准字段，从 HTML 元素中按约定提取。

    注意：此方法是通用实现，各网站具体选择器在子类中覆写 extract_fields 方法。

    Args:
        item: BeautifulSoup Tag 对象
        adapter: 网站适配器

    Returns:
        标准评论字典
    """
    # 默认实现：尝试从 item.text 获取纯文本
    # 实际各网站子类应覆写此逻辑
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
    按点号分隔的路径从嵌套字典中取值。

    用于从 JSON API 响应中提取深层嵌套的数据。

    Args:
        data: 嵌套字典
        path: 点号分隔路径，如 "data.list" 或 "result.data.comments"

    Returns:
        路径对应的值，如果中途取不到则返回 None

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
            # 支持从列表中按索引取值，如 "data.0.items"
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

    Args:
        url: 完整的携程页面 URL

    Returns:
        提取到的数字 ID 字符串，未匹配时返回 None
    """
    import re

    # 景点 PC 端: /sight/地区英文/数字.html
    m = re.search(r'/sight/[^/]+/(\d+)', url)
    if m:
        return m.group(1)

    # 景点 M 站: /webapp/you/sight/数字/
    m = re.search(r'/sight/(\d+)(?:/|\.html)', url)
    if m:
        return m.group(1)

    # 度假产品: /travel/detail/p数字 或 /p数字.html
    m = re.search(r'/p(\d{5,})(?:\.html)?', url)
    if m:
        return m.group(1)

    # 兜底：取 URL 中最后一串连续数字（至少 4 位）
    m = re.search(r'/(\d{4,})(?:\.html|/)', url)
    if m:
        return m.group(1)

    return None


def _apply_field_mapping(item: dict, mapping: dict) -> dict:
    """
    将原始字段名映射为标准字段名。

    只保留在 mapping 中出现的字段（标准字段），
    未在 mapping 中的字段会被丢弃。
    如果标准字段在原始数据中不存在，使用空值。

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
