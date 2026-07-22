"""
模块名称：网站配置服务

功能说明：
    - 提供预设网站列表
    - 根据网站标识获取适配器
    - 供 UI 层选择网站时使用
"""

import logging

from src.sites import (
    get_site_adapter, get_preset_sites,
    get_crawl_types, get_sites_by_crawl_type,
)

logger = logging.getLogger("tour-crawler.site_service")


class SiteService:
    """
    网站配置服务。

    提供预设网站的信息查询功能。
    """

    def get_preset_sites(self) -> list[dict]:
        """
        获取所有预设网站的信息列表。

        Returns:
            网站信息列表，每个元素包含 name、display_name、domain

        Example:
            >>> service.get_preset_sites()
            [
                {"name": "ctrip", "display_name": "携程", "domain": ".ctrip.com"},
                {"name": "ctrip", "display_name": "携程", "domain": ".ctrip.com"},
            ]
        """
        return get_preset_sites()

    def get_site(self, site_name: str) -> dict | None:
        """
        获取指定网站的详细信息。

        Args:
            site_name: 网站标识

        Returns:
            网站信息字典，未找到时返回 None
        """
        adapter = get_site_adapter(site_name)
        if adapter is None:
            return None

        return {
            "name": adapter.site_name,
            "display_name": adapter.site_display_name,
            "domain": adapter.domain,
            "login_url": adapter.login_url,
            "cookie_platform": adapter.cookie_platform or adapter.site_name,
        }

    def get_crawl_types(self) -> list[dict]:
        """
        获取所有爬取类型列表。

        Returns:
            爬取类型信息列表，每项包含 key 和 display_name
        """
        return get_crawl_types()

    def get_sites_by_crawl_type(self, crawl_type: str) -> list[dict]:
        """
        获取指定爬取类型下的站点列表。

        Args:
            crawl_type: 爬取类型标识

        Returns:
            站点信息字典列表
        """
        return get_sites_by_crawl_type(crawl_type)

    def validate_site(self, site_name: str) -> bool:
        """
        验证网站标识是否在预设列表中。

        Args:
            site_name: 网站标识

        Returns:
            True 表示是支持的网站
        """
        return get_site_adapter(site_name) is not None
