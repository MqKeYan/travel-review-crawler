"""
模块名称：携程（Ctrip）共享爬虫逻辑

功能说明：
    - 携程景点/旅游共用的 DOM 提取和 URL 工具
    - 第 1 页：从 __NEXT_DATA__ JSON 或 DOM 提取
    - 第 2+ 页：由各自适配器的 Selenium 爬虫负责
    - Cookie 统一使用携程登录态
"""

import re
import json
import time
import logging

from src.models.review import EMPTY_REVIEW
from src.utils.image_utils import extract_img_url_from_tag

logger = logging.getLogger("tour-crawler.sites.ctrip")


# ==================== JSON 提取（第 1 页） ====================

def _parse_publish_time(publish_time: str) -> str:
    """解析携程发布时间格式并返回标准化日期: YYYY-MM-DD"""
    if not publish_time:
        return ""
    try:
        # 格式: 2025-06-14 / 2025-06-14 12:30:00
        return publish_time.strip()[:10]
    except Exception:
        return ""


def _extract_comment(item: dict) -> dict:
    """将 __NEXT_DATA__ 中的单条评论 JSON 转为标准格式"""
    review = EMPTY_REVIEW.copy()

    review["username"] = (item.get("userInfo") or {}).get("userName") or ""
    review["content"] = item.get("content") or ""
    review["rating"] = int(item.get("score") or 0)
    review["time"] = _parse_publish_time(item.get("publishTime") or "")
    review["ip_location"] = item.get("ipLocationName") or ""

    # 图片列表
    images = item.get("images") or []
    if images:
        review["image_urls"] = [img.get("imageUrl") or "" for img in images if img.get("imageUrl")]

    # 商家回复
    reply = item.get("reply") or {}
    if reply.get("replyContent"):
        review["merchant_reply"] = reply["replyContent"]

    return review


def extract_from_next_data(html_text: str) -> list[dict]:
    """从页面 __NEXT_DATA__ JSON 中提取评论（携程景点首页）"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return []
        data = json.loads(script.string)
        comments = (
            data.get("props", {})
            .get("pageProps", {})
            .get("resourceInfo", {})
            .get("commentInfo", {})
            .get("commentList", [])
        )
        if not comments:
            return []
        return [_extract_comment(c) for c in comments]
    except Exception:
        return []


def extract_from_dom(html_text: str) -> list[dict]:
    """从 HTML DOM 解析携程景点评论（CSS 选择器方式）"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "lxml")
        items = soup.select(".commentItem")
        reviews = []
        for item in items:
            review = EMPTY_REVIEW.copy()

            # 用户名
            name_el = item.select_one(".userName")
            if name_el:
                review["username"] = name_el.get_text(strip=True)

            # 评分
            star_el = item.select_one(".starNum")
            if star_el:
                try:
                    review["rating"] = int(star_el.get_text(strip=True))
                except ValueError:
                    pass

            # 时间
            time_el = item.select_one(".time")
            if time_el:
                review["time"] = _parse_publish_time(time_el.get_text(strip=True))

            # 内容
            content_el = item.select_one(".commentDetail")
            if content_el:
                review["content"] = content_el.get_text(strip=True)

            # IP 属地
            ip_el = item.select_one(".ipLocation")
            if ip_el:
                review["ip_location"] = ip_el.get_text(strip=True)

            # 图片
            img_els = item.select(".commentImg img")
            img_urls = []
            for img in img_els:
                src = extract_img_url_from_tag(img)
                if src:
                    img_urls.append(src)
            review["image_urls"] = img_urls

            reviews.append(review)
        return reviews
    except Exception:
        return []


# ==================== 携程旅游 DOM 提取 ====================

def _extract_ip_and_time(vacation_text: str) -> tuple[str, str]:
    """从携程旅游评论的底部信息中提取 IP 属地和出游时间"""
    ip_location = ""
    travel_date = ""
    if not vacation_text:
        return ip_location, travel_date
    parts = [p.strip() for p in vacation_text.split("|") if p.strip()]
    for part in parts:
        if "出发" in part:
            travel_date = part.replace("出发", "").strip()
        elif len(part) <= 10 and not part.startswith("IP"):
            ip_location = part
    return ip_location, travel_date


def extract_from_vacation_dom(html_text: str) -> list[dict]:
    """从 HTML DOM 解析携程旅游产品评论"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "lxml")
        items = soup.select(".ct-review-list-item")
        reviews = []
        for item in items:
            review = EMPTY_REVIEW.copy()

            # 用户名
            name_el = item.select_one(".ct-review-name")
            if name_el:
                review["username"] = name_el.get_text(strip=True)

            # 评分
            star_els = item.select(".ct-review-star-box .active")
            if star_els:
                review["rating"] = len(star_els)

            # 内容
            content_el = item.select_one(".ct-review-content")
            if content_el:
                review["content"] = content_el.get_text(strip=True)

            # 时间
            time_el = item.select_one(".ct-review-time")
            if time_el:
                review["time"] = _parse_publish_time(time_el.get_text(strip=True))

            # IP / 出游信息
            meta_el = item.select_one(".ct-review-info")
            meta_text = meta_el.get_text(strip=True) if meta_el else ""
            ip_loc, travel = _extract_ip_and_time(meta_text)
            review["ip_location"] = ip_loc
            review["travel_date"] = travel

            # 图片
            img_els = item.select(".ct-review-img img, .ct-review-pic img")
            img_urls = []
            for img in img_els:
                src = extract_img_url_from_tag(img)
                if src:
                    img_urls.append(src)
            review["image_urls"] = img_urls

            reviews.append(review)
        return reviews
    except Exception:
        return []


# ==================== URL 工具 ====================

def extract_url_params(url: str) -> dict[str, str]:
    """从携程景点 URL 中提取关键参数（域名+资源ID）"""
    from urllib.parse import urlparse
    from src.sites.base import extract_resource_id
    params = {}
    try:
        host = urlparse(url).netloc.lower()
        if "vacations.ctrip.com" in host:
            params["domain"] = "vacations.ctrip.com"
        else:
            params["domain"] = "you.ctrip.com"
    except Exception:
        pass
    rid = extract_resource_id(url)
    if rid:
        params["id"] = rid
    # 提取路径中的城市/景点名部分
    m = re.search(r'/sight/([^/]+)/', url)
    if m:
        params["location"] = m.group(1)
    return params


def build_ctrip_url(domain: str, id: str, location: str = "") -> str:
    """用提取的参数构造干净的携程景点 URL"""
    if location:
        return f"https://{domain}/sight/{location}/{id}.html"
    return f"https://{domain}/sight/{id}.html"


def extract_reviews_from_html(html_text: str) -> list[dict]:
    """
    从 HTML 提取评论（供 raw_html_parser 使用）。
    优先从 __NEXT_DATA__ 提取，回退到 DOM 解析。
    """
    reviews = extract_from_next_data(html_text)
    if reviews:
        return reviews
    return extract_from_dom(html_text)


# ==================== Cookie 注入 ====================

def inject_ctrip_cookies(driver, cookie_file: str) -> bool:
    """加载携程 Cookie 并注入浏览器，统一从 ctrip 目录读取"""
    if not cookie_file:
        return False

    try:
        from src.engine.cookie_manager import load_cookies_from_file

        cookies = load_cookies_from_file("ctrip", cookie_file.replace(".json", ""))
        if not cookies:
            logger.warning(f"未找到 Cookie 文件: ctrip/{cookie_file}")
            return False

        # 先访问携程首页建立域上下文
        driver.get("https://www.ctrip.com")

        added = 0
        for c in cookies:
            try:
                cookie_dict = {
                    "name": c["name"],
                    "value": c["value"],
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                }
                if c.get("domain"):
                    cookie_dict["domain"] = c["domain"]
                driver.add_cookie(cookie_dict)
                added += 1
            except Exception:
                pass

        logger.info(f"Cookie 注入成功: ctrip/{cookie_file} ({added} 条)")
        return added > 0
    except Exception as e:
        logger.warning(f"Cookie 注入失败: {e}")
        return False
