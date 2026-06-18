"""
模块名称：去哪儿（Qunar）网站适配器

功能说明：
    - 去哪儿网旅游景点评论页面的适配规则
    - 去哪儿评论通过 JSON API 获取
    - 定义 URL 结构、请求参数、字段映射

使用说明：
    去哪儿景点评论 API 模板：
    https://travel.qunar.com/api/comment/{poi_id}/list
"""

from src.sites.base import SiteAdapter, RequestType, HttpMethod


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
        request_type=RequestType.JSON_API,
        http_method=HttpMethod.GET,
        api_endpoint="https://travel.qunar.com/api/comment/{poi_id}/list",
        api_params_template={
            "page": "{page}",
            "pageSize": 20,
            "sort": "1",
        },
        page_size=20,
        page_start=1,
        max_pages_limit=100,
        field_mapping={
            "userName": "username",
            "content": "content",
            "score": "rating",
            "addTime": "time",
            "userLevel": "user_level",
            "praiseNum": "likes",
            "replyNum": "reply_count",
            "travelType": "travel_type",
            "merchantReply": "merchant_reply",
            "location": "ip_location",
            "imgList": "image_urls",
        },
        reviews_json_path="data.list",
        total_count_json_path="data.totalCount",
    )
