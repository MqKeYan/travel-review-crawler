"""
网站适配层包，提供预设网站的适配器。

每个适配器通过工厂函数创建，配置该网站特有的请求参数和解析规则。
适配器按爬取类型-目标网站二级结构组织在子包中。

出口函数：
    get_site_adapter(site_name: str) -> SiteAdapter | None
    get_preset_sites() -> list[dict]
    get_crawl_types() -> list[dict]
    get_sites_by_crawl_type(crawl_type: str) -> list[dict]
    recognize_crawl_type(url: str) -> str | None
"""

from urllib.parse import urlparse

from src.sites.base import SiteAdapter, HttpMethod

# 爬取类型定义
_CRAWL_TYPE_INFO = {
    "scenic":   {"key": "scenic",   "display_name": "旅游景点", "domains": [".ctrip.com", ".fliggy.com"]},
    "shopping": {"key": "shopping", "display_name": "购物网站", "domains": ["detail.tmall.com", "item.taobao.com"]},
    "hotel":    {"key": "hotel",    "display_name": "酒店民宿", "domains": ["hotels.ctrip.com"]},
}
_CRAWL_TYPE_ORDER = ["shopping", "scenic", "hotel"]

# 预设网站适配器注册表（工厂函数 + 单例缓存）
_SITE_REGISTRY: dict[str, SiteAdapter] = {}


def _ensure_registry() -> None:
    """确保注册表已初始化（惰性加载），从子包收集所有适配器。"""
    if _SITE_REGISTRY:
        return

    # 子包名 → 爬取类型 key 映射
    _SUB_PACKAGE_MAP = {
        "scenic": "scenic",
        "shopping": "shopping",
        "hotel": "hotel",
    }

    for sub_pkg, crawl_type_key in _SUB_PACKAGE_MAP.items():
        try:
            mod = __import__(f"src.sites.{sub_pkg}", fromlist=["register_adapters"])
            adapters = mod.register_adapters()
            _SITE_REGISTRY.update(adapters)
        except ImportError:
            pass  # 子包不存在时跳过（预留分类）


def get_site_adapter(site_name: str) -> SiteAdapter | None:
    """
    根据网站标识获取对应的适配器实例。

    Args:
        site_name: 网站标识（如 "ctrip"、"fliggy"）

    Returns:
        网站适配器实例，未找到时返回 None
    """
    _ensure_registry()
    return _SITE_REGISTRY.get(site_name.lower())


def get_preset_sites() -> list[dict]:
    """
    获取所有预设网站的信息列表。

    Returns:
        网站信息字典列表，每项包含 name、display_name、domain、crawl_type

    Example:
        >>> get_preset_sites()
        [{"name": "ctrip", "display_name": "携程", "domain": ".ctrip.com", "crawl_type": "scenic"}, ...]
    """
    _ensure_registry()
    return [
        {
            "name": adapter.site_name,
            "display_name": adapter.site_display_name,
            "domain": adapter.domain,
            "url_template": adapter.url_template,
            "crawl_type": adapter.crawl_type,
        }
        for adapter in _SITE_REGISTRY.values()
    ]


def get_crawl_types() -> list[dict]:
    """
    获取所有爬取类型列表。

    Returns:
        爬取类型信息列表，每项包含 key 和 display_name

    Example:
        >>> get_crawl_types()
        [{"key": "shopping", "display_name": "购物网站"}, ...]
    """
    return [
        {"key": info["key"], "display_name": info["display_name"]}
        for key in _CRAWL_TYPE_ORDER
        for info in [_CRAWL_TYPE_INFO[key]]
    ]


def get_sites_by_crawl_type(crawl_type: str) -> list[dict]:
    """
    获取指定爬取类型下的所有站点信息。

    Args:
        crawl_type: 爬取类型标识（"scenic" / "shopping" / "hotel"）

    Returns:
        站点信息字典列表
    """
    _ensure_registry()
    return [
        {
            "name": adapter.site_name,
            "display_name": adapter.site_display_name,
            "domain": adapter.domain,
            "url_template": adapter.url_template,
            "crawl_type": adapter.crawl_type,
        }
        for adapter in _SITE_REGISTRY.values()
        if adapter.crawl_type == crawl_type
    ]


def recognize_crawl_type(url: str) -> str | None:
    """
    通过 URL 域名识别爬取类型。

    Args:
        url: 目标 URL

    Returns:
        爬取类型标识（"scenic"/"shopping"/"hotel"），未识别返回 None
    """
    if not url or not url.startswith("http"):
        return None
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None

    # 收集所有域名，按长度降序（优先匹配更具体的域名如 hotels.ctrip.com）
    pairs = []
    for key, info in _CRAWL_TYPE_INFO.items():
        for domain in info["domains"]:
            if domain:
                pairs.append((len(domain), key, domain.lstrip(".")))
    pairs.sort(reverse=True)
    for _, key, domain in pairs:
        if host.endswith(domain):
            return key
    return None


def get_crawl_type_domains(crawl_type: str) -> list[str]:
    """
    获取指定爬取类型的所有匹配域名。

    Args:
        crawl_type: 爬取类型标识

    Returns:
        域名列表（不含前导点），未找到返回空列表
    """
    info = _CRAWL_TYPE_INFO.get(crawl_type, {})
    return [d.lstrip(".") for d in info.get("domains", [])]


__all__ = [
    "SiteAdapter", "HttpMethod",
    "get_site_adapter", "get_preset_sites",
    "get_crawl_types", "get_sites_by_crawl_type",
    "recognize_crawl_type", "get_crawl_type_domains",
    "get_crawl_types", "get_sites_by_crawl_type",
    "recognize_crawl_type",
]
