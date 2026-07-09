"""
模块名称：旅游景点分类站点集合

功能说明：
    - 聚合旅游景点分类下的所有站点适配器
    - 提供 register_adapters() 供父级注册表调用
"""

from src.sites.scenic.ctrip import create_ctrip_adapter
from src.sites.scenic.fliggy import create_fliggy_adapter


def register_adapters() -> dict:
    """
    注册旅游景点分类下的所有适配器。

    Returns:
        {site_name: SiteAdapter} 字典
    """
    ctrip = create_ctrip_adapter()
    fliggy = create_fliggy_adapter()
    return {ctrip.site_name: ctrip, fliggy.site_name: fliggy}


__all__ = ["register_adapters", "create_ctrip_adapter", "create_fliggy_adapter"]
