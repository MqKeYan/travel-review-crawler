"""
模块名称：飞猪（Fliggy）网站适配器

功能说明：
    - 飞猪旅游景点评论页面的适配规则
    - 飞猪评论通过 JSON API 接口获取
    - 定义 URL 结构、请求参数、字段映射

使用说明：
    飞猪景点评论 API 模板：
    https://travel.fliggy.com/api/comment/list
"""

from src.sites.base import SiteAdapter, RequestType, HttpMethod


def create_fliggy_adapter() -> SiteAdapter:
    """
    创建飞猪网适配器实例。

    Returns:
        配置完成的飞猪适配器
    """
    return SiteAdapter(
        site_name="fliggy",
        site_display_name="飞猪",
        domain=".fliggy.com",
        login_url="https://login.fliggy.com/login.htm",
        request_type=RequestType.JSON_API,
        http_method=HttpMethod.GET,
        api_endpoint="https://travel.fliggy.com/api/comment/list",
        api_params_template={
            "page": "{page}",
            "pageSize": 20,
            "order": "1",
        },
        page_size=20,
        page_start=1,
        max_pages_limit=100,
        field_mapping={
            "userNick": "username",
            "content": "content",
            "ratingScore": "rating",
            "gmtCreate": "time",
            "userLevel": "user_level",
            "supportCount": "likes",
            "replyCount": "reply_count",
            "travelType": "travel_type",
            "merchantReply": "merchant_reply",
            "ipLocation": "ip_location",
            "imageUrls": "image_urls",
        },
        reviews_json_path="data.resultList",
        total_count_json_path="data.totalCount",
    )
