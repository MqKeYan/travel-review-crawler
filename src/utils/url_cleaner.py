"""
模块名称：URL 清理工具

功能说明：
    - 各站点的 URL 参数提取与构造
    - 去除无关参数（追踪参数、会话参数等）
    - 供任务详情显示和爬虫内部使用
"""

import importlib
import logging

logger = logging.getLogger("tour-crawler.url_cleaner")

# 站点名 → (模块路径, 构造参数列表, 构造函数名)
_SITE_URL_CONFIG = {
    "taobao":      ("src.sites.shopping.taobao",   ["domain", "id", "mi_id"], "build_taobao_url"),
    "fliggy":      ("src.sites.scenic.fliggy",     ["domain", "id"],          "build_fliggy_url"),
    "ctrip":       ("src.sites.scenic.ctrip",      ["domain", "id", "location"], "build_ctrip_url"),
    "ctrip_hotel": ("src.sites.hotel.ctrip_hotel", ["domain", "id"],          "build_ctrip_hotel_url"),
}


def clean_task_url(site: str, target_url: str) -> str:
    """
    用站点各自的URL构造逻辑返回干净URL，去除无关参数。
    未注册的站点返回原始URL。

    Args:
        site: 站点标识（"taobao" / "fliggy" / "ctrip" / "ctrip_hotel"）
        target_url: 用户输入的原始 URL

    Returns:
        构造后的干净 URL
    """
    config = _SITE_URL_CONFIG.get(site)
    if not config:
        return target_url

    module_path, required_keys, build_func_name = config
    try:
        mod = importlib.import_module(module_path)
        params = mod.extract_url_params(target_url)
        if not params.get("id"):
            return target_url
        build_func = getattr(mod, build_func_name)
        kwargs = {k: params.get(k, "") for k in required_keys}
        return build_func(**kwargs)
    except Exception:
        logger.debug(f"清理 URL 失败 [{site}]: {target_url}", exc_info=True)
        return target_url
