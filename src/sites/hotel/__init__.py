"""
模块名称：酒店民宿分类站点集合

功能说明：
    - 聚合酒店民宿分类下的所有站点适配器
    - 提供 register_adapters() 供父级注册表调用
"""

from src.sites.hotel.ctrip_hotel import create_ctrip_hotel_adapter


def register_adapters() -> dict:
    """注册酒店民宿分类下的适配器"""
    ctrip_hotel = create_ctrip_hotel_adapter()
    return {ctrip_hotel.site_name: ctrip_hotel}


__all__ = ["register_adapters", "create_ctrip_hotel_adapter"]
