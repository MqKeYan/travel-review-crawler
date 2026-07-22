"""
模块名称：天猫（Tmall）网站适配器

功能说明：
    - 天猫商品评论页面适配器
    - 爬虫核心逻辑在 _ali_base.py，与淘宝共用
    - Cookie 统一使用淘宝登录态（天猫使用淘宝账号登录）

URL 格式：
    https://detail.tmall.com/item.htm?id=XXXXX&mi_id=XXXXX
"""

from src.sites.base import SiteAdapter, HttpMethod
from src.sites.shopping._ali_base import selenium_crawl_taobao


def _validate_tmall_url(url: str) -> tuple[bool, str]:
    """校验是否为有效的天猫商品 URL（必须包含 id 和 mi_id 参数）"""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return (False, "无法解析 URL")

    valid_hosts = ["detail.tmall.com"]
    if not any(h in host for h in valid_hosts):
        return (False, "仅支持 detail.tmall.com 的天猫商品评价页面")
    if "id=" not in url:
        return (False, "URL 缺少商品 id 参数")
    if "mi_id=" not in url:
        return (False, "URL 缺少 mi_id 参数（天猫商品页必需）")
    return (True, "")


def create_tmall_adapter() -> SiteAdapter:
    """创建天猫适配器实例"""
    return SiteAdapter(
        site_name="tmall",
        site_display_name="天猫",
        crawl_type="shopping",
        domain=".tmall.com",
        login_url="https://login.taobao.com/member/login.jhtml",
        url_template="https://detail.tmall.com/item.htm?id={id}&mi_id={mi_id}",
        http_method=HttpMethod.GET,
        page_size=20,
        page_start=1,
        max_pages_limit=99999,
        review_selector="",
        raw_html_parser=None,
        selenium_crawler=selenium_crawl_taobao,
        url_validator=_validate_tmall_url,
        field_mapping={},
        login_cookie_names=("login_uid", "S_token", "dper", "unb", "cookie2"),
    )
