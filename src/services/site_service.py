"""
模块名称：网站配置服务

功能说明：
    - 提供预设网站列表
    - 根据网站标识获取适配器
    - 供 UI 层选择网站时使用
"""

import logging

from src.sites import get_site_adapter, get_preset_sites

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
                {"name": "dianping", "display_name": "大众点评", "domain": ".dianping.com"},
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
        }

    def validate_site(self, site_name: str) -> bool:
        """
        验证网站标识是否在预设列表中。

        Args:
            site_name: 网站标识

        Returns:
            True 表示是支持的网站
        """
        return get_site_adapter(site_name) is not None
