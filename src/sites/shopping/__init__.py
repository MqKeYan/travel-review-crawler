"""
模块名称：购物网站分类站点集合

功能说明：
    - 注册购物网站分类下的站点适配器
    - 当前包含：淘宝/天猫
"""

from src.sites.shopping.taobao import create_taobao_adapter


def register_adapters() -> dict:
    """注册购物网站分类下的适配器"""
    taobao = create_taobao_adapter()
    return {taobao.site_name: taobao}


__all__ = ["register_adapters"]
