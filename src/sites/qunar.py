"""
模块名称：去哪儿（Qunar）网站适配器

功能说明：
    - 去哪儿网旅游景点评论页面的适配规则
    - 通过 HTML 页面解析获取评论
    - 定义 URL 结构、字段映射

使用说明：
    去哪儿景点评论页面需要有效的登录 Cookie，
    评论数据渲染在 HTML DOM 中直接提取。
"""

from src.sites.base import SiteAdapter, HttpMethod


def create_qunar_adapter() -> SiteAdapter:
    """
    创建去哪儿网适配器实例。

    Returns:
        配置完成的去哪儿适配器
    """
    return SiteAdapter(
        site_name="qunar",
        site_display_name="去哪儿",
        domain=".qunar.com",
        login_url="https://user.qunar.com/",
        url_template="https://travel.qunar.com/p-oi{id}.html",
        http_method=HttpMethod.GET,
        page_size=20,
        page_start=1,
        max_pages_limit=100,
        field_mapping={
            "userName": "username",
            "content": "content",
            "score": "rating",
            "addTime": "time",
            "userLevel": "user_level",
            "location": "ip_location",
            "imgList": "image_urls",
        },
    )
