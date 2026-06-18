"""
模块名称：美团（Meituan）网站适配器

功能说明：
    - 美团旅游景点评论页面的适配规则
    - 美团评论通过 JSON API 接口获取
    - 定义 URL 结构、请求参数、字段映射

使用说明：
    美团景点评论 API 模板：
    https://www.meituan.com/api/v2/poi/{poi_id}/reviews
"""

from src.sites.base import SiteAdapter, RequestType, HttpMethod


def create_meituan_adapter() -> SiteAdapter:
    """
    创建美团网适配器实例。

    Returns:
        配置完成的美团适配器
    """
    return SiteAdapter(
        site_name="meituan",
        site_display_name="美团",
        domain=".meituan.com",
        login_url="https://passport.meituan.com/account/login",
        request_type=RequestType.JSON_API,
        http_method=HttpMethod.GET,
        api_endpoint="https://www.meituan.com/api/v2/poi/{poi_id}/reviews",
        api_params_template={
            "page": "{page}",
            "pageSize": 20,
            "sortType": "1",
        },
        page_size=20,
        page_start=1,
        max_pages_limit=100,
        field_mapping={
            "nickname": "username",
            "comment": "content",
            "star": "rating",
            "addTime": "time",
            "userLevel": "user_level",
            "likeCount": "likes",
            "replyCount": "reply_count",
            "tripType": "travel_type",
            "merchantReply": "merchant_reply",
            "ipLocation": "ip_location",
            "images": "image_urls",
        },
        reviews_json_path="data.reviews",
        total_count_json_path="data.total",
    )
