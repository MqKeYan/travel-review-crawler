"""
网站适配层包，提供预设网站的适配器。

每个适配器通过工厂函数创建，配置该网站特有的请求参数和解析规则。

出口函数：
    get_site_adapter(site_name: str) -> SiteAdapter | None
    get_preset_sites() -> list[dict]
"""

from src.sites.base import SiteAdapter, HttpMethod
from src.sites.ctrip import create_ctrip_adapter
from src.sites.fliggy import create_fliggy_adapter
from src.sites.dianping import create_dianping_adapter

# 预设网站适配器注册表（工厂函数 + 单例缓存）
_SITE_REGISTRY: dict[str, SiteAdapter] = {}


def _ensure_registry() -> None:
    """确保注册表已初始化（惰性加载）"""
    if not _SITE_REGISTRY:
        _SITE_REGISTRY.update({
            "ctrip": create_ctrip_adapter(),
            "fliggy": create_fliggy_adapter(),
            "dianping": create_dianping_adapter(),
        })


def get_site_adapter(site_name: str) -> SiteAdapter | None:
    """
    根据网站标识获取对应的适配器实例。

    Args:
        site_name: 网站标识（"ctrip" / "fliggy" / "dianping"）

    Returns:
        网站适配器实例，未找到时返回 None
    """
    _ensure_registry()
    return _SITE_REGISTRY.get(site_name.lower())


def get_preset_sites() -> list[dict]:
    """
    获取所有预设网站的信息列表。

    Returns:
        网站信息字典列表，每项包含 name、display_name、domain

    Example:
        >>> get_preset_sites()
        [{"name": "ctrip", "display_name": "携程", "domain": ".ctrip.com"}, ...]
    """
    _ensure_registry()
    return [
        {
            "name": adapter.site_name,
            "display_name": adapter.site_display_name,
            "domain": adapter.domain,
            "url_template": adapter.url_template,
        }
        for adapter in _SITE_REGISTRY.values()
    ]


__all__ = [
    "SiteAdapter", "HttpMethod",
    "get_site_adapter", "get_preset_sites",
]
