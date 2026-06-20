"""
模块名称：携程（Ctrip）网站适配器

功能说明：
    - 携程景点评论页面的适配规则
    - 第 1 页：从 __NEXT_DATA__ JSON 提取（快速，10 条）
    - 第 2+ 页：Selenium 驱动浏览器点击「下一页」提取（需 Cookie）
    - 需要携程 Cookie（通过 Selenium 获取）

API 接口已确认均不可用：
    - getCommentList → 403 Forbidden
    - viewCommentList → data: null
    - getCommentCollapseList → 参数错误
    - commentWeb → 返回 HTML 而非 JSON
"""

import re
import json
import time
import logging

from src.sites.base import SiteAdapter, HttpMethod
from src.models.review import EMPTY_REVIEW

logger = logging.getLogger("tour-crawler.sites.ctrip")


# ==================== JSON 提取（第 1 页） ====================


def _parse_publish_time(publish_time: str) -> str:
    if not publish_time or not isinstance(publish_time, str):
        return ""
    import datetime
    m = re.search(r"(\d{10})", publish_time)
    if m:
        ts = int(m.group(1))
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    return ""


def _extract_comment(item: dict) -> dict:
    """从 __NEXT_DATA__ 的 commentList 单条 JSON 映射为标准字段"""
    review = EMPTY_REVIEW.copy()

    user_info = item.get("userInfo") or {}
    review["username"] = user_info.get("userNick", "")
    review["avatar_url"] = user_info.get("userImage", "")
    review["user_level"] = user_info.get("userMember", "")

    score = item.get("score", 0)
    try:
        review["rating"] = int(score)
    except (ValueError, TypeError):
        review["rating"] = 0
    review["rating_label"] = "好评" if review["rating"] >= 4 else ("中评" if review["rating"] >= 3 else "差评")

    scores = item.get("scores") or []
    if scores:
        parts = [f"{s.get('name', '')}:{s.get('score', '')}" for s in scores if s.get('name') and s.get('score')]
        review["sub_scores"] = " | ".join(parts)

    review["content"] = item.get("content", "")
    review["time"] = _parse_publish_time(item.get("publishTime", ""))
    review["travel_type"] = item.get("touristTypeDisplay") or ""

    images = item.get("images") or []
    review["image_urls"] = [img.get("imageSrcUrl", "") for img in images if isinstance(img, dict)]
    review["ip_location"] = item.get("ipLocatedName", "")

    useful = item.get("usefulCount", 0)
    review["likes"] = int(useful) if useful else 0
    reply_count = item.get("replyCount", 0)
    review["reply_count"] = int(reply_count) if reply_count else 0
    review["merchant_reply"] = item.get("replyContent") or ""

    return review


def extract_from_next_data(html_text: str) -> list[dict]:
    """从 __NEXT_DATA__ JSON 提取评论"""
    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        comments = (data.get("props", {}).get("pageProps", {})
                    .get("initialState", {}).get("commentList", []))
        return [_extract_comment(c) for c in comments] if comments else []
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


# ==================== HTML DOM 提取（第 2+ 页 / 回退） ====================


def extract_from_dom(html_text: str) -> list[dict]:
    """从 HTML DOM 的 .commentItem 提取评论"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, "lxml")
    items = soup.select(".commentItem")
    if not items:
        return []

    reviews = []
    for item in items:
        r = EMPTY_REVIEW.copy()
        name_el = item.select_one(".userName")
        if name_el:
            r["username"] = name_el.get_text(strip=True)
        img_el = item.select_one(".userImg")
        if img_el:
            r["avatar_url"] = img_el.get("src", "")
        score_el = item.select_one(".averageScore")
        if score_el:
            txt = score_el.get_text(strip=True)
            m2 = re.search(r"(\d+[\._]?\d*)", txt)
            if m2:
                try:
                    r["rating"] = float(m2.group(1).replace("_", "."))
                except ValueError:
                    pass
            r["rating_label"] = "好评" if "超棒" in txt or "好评" in txt else ("差评" if "差" in txt else "中评")
        content_el = item.select_one(".commentDetail")
        if content_el:
            r["content"] = content_el.get_text(strip=True)
        img_items = item.select(".commentImgList a img")
        if img_items:
            r["image_urls"] = [img.get("src", "") for img in img_items]
        time_el = item.select_one(".commentTime")
        if time_el:
            elc = time_el.__copy__()
            for child in list(elc.children):
                if child.name is not None:
                    child.decompose()
            r["time"] = elc.get_text(strip=True)
        ip_el = item.select_one(".ipContent")
        if ip_el:
            r["ip_location"] = ip_el.get_text(strip=True).replace("IP属地：", "").replace("IP属地:", "").strip()
        for tool in item.select(".toolsItem"):
            if "reportItem" in tool.get("class", []):
                continue
            m3 = re.search(r"(\d+)", tool.get_text(strip=True))
            if m3:
                r["likes"] = int(m3.group(1))
                break
        reviews.append(r)
    return reviews


# ==================== Selenium 真翻页爬取 ====================


def _dedup_reviews(reviews: list[dict]) -> list[dict]:
    """基于用户名+内容前100字去重"""
    seen = set()
    result = []
    for r in reviews:
        key = (r.get("username", ""), r.get("content", "")[:100], r.get("time", ""))
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def selenium_crawl_ctrip(url: str, max_pages: int = 10, max_count: int = 0,
                         timeout: int = 300, stop_check=None,
                         progress_callback=None, cookie_file=None) -> list[dict]:
    """
    通过 Selenium 驱动 Edge 浏览器，点击「下一页」翻页爬取携程评论。

    Args:
        url: 景点页面 URL
        max_pages: 最大翻页数
        max_count: 最大条数限制（0 表示不限）
        timeout: 总超时秒数
        stop_check: 停止检测回调，返回 True 时中断翻页
        progress_callback: 进度回调 (page_num, count, total, message)

    Returns:
        去重后的评论列表
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
    except ImportError:
        logger.error("Selenium 未安装，无法翻页爬取")
        return []

    options = Options()
    options.add_argument("--headless=new")  # 无头模式，后台静默运行
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Edge(options=options)
    all_reviews = []
    start_time = time.time()

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        for page in range(1, max_pages + 1):
            # 检查外部停止请求
            if stop_check and stop_check():
                logger.info("Selenium 翻页被外部停止")
                break

            # 检查是否达到最大条数
            if max_count and len(all_reviews) >= max_count:
                logger.info(f"已达到目标条数 {max_count}，停止翻页")
                break

            if time.time() - start_time > timeout:
                logger.warning("翻页超时")
                break

            # 等待评论容器加载
            try:
                wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".commentItem"))
            except TimeoutException:
                logger.warning(f"第 {page} 页等待评论加载超时")
                break

            time.sleep(1)  # 额外等待渲染完成

            # 提取当前页评论
            html = driver.page_source
            page_reviews = extract_from_dom(html)

            if page == 1:
                # 第 1 页优先用 __NEXT_DATA__（数据更全）
                next_data = extract_from_next_data(html)
                page_reviews = next_data if next_data else page_reviews

            before = len(all_reviews)
            all_reviews.extend(page_reviews)
            # 达到 max_count 时只保留目标条数
            if max_count and len(all_reviews) > max_count:
                all_reviews = all_reviews[:max_count]
            all_reviews = _dedup_reviews(all_reviews)
            new_count = len(all_reviews) - before

            logger.info(f"第 {page} 页: 提取 {len(page_reviews)} 条（新增 {new_count} 条，累计 {len(all_reviews)} 条）")

            # 每页回传进度
            if progress_callback:
                progress_callback(
                    page_num=page, count=new_count, total=len(all_reviews),
                    message=f"正在爬取第 {page} 页...（累计 {len(all_reviews)} 条）"
                )

            # 检查是否已达到目标
            if max_count and len(all_reviews) >= max_count:
                break

            # 判断是否还有下一页
            if page < max_pages:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, ".ant-pagination-next:not(.ant-pagination-disabled)")
                    # 用 JavaScript 点击，避免元素被遮挡
                    driver.execute_script("arguments[0].click();", next_btn)
                    # 等待新评论加载（评论数增加或内容变化）
                    time.sleep(1.5)
                except NoSuchElementException:
                    logger.info("已到末页，翻页结束")
                    break
            else:
                break

    except Exception as e:
        logger.error(f"Selenium 翻页异常: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return all_reviews


# ==================== 适配器入口 ====================


def extract_reviews_from_html(html_text: str) -> list[dict]:
    """
    从 HTML 提取评论（供 raw_html_parser 使用）。
    优先从 __NEXT_DATA__ 提取，回退到 DOM 解析。
    """
    reviews = extract_from_next_data(html_text)
    if reviews:
        return reviews
    return extract_from_dom(html_text)


def create_ctrip_adapter() -> SiteAdapter:
    """
    创建携程网适配器实例。

    第 1 页快速提取（requests + __NEXT_DATA__），
    第 2+ 页通过 Selenium 真翻页。

    Returns:
        配置完成的携程适配器
    """
    return SiteAdapter(
        site_name="ctrip",
        site_display_name="携程",
        domain=".ctrip.com",
        login_url="https://passport.ctrip.com/user/login",
        url_template="https://you.ctrip.com/sight/{id}.html",
        http_method=HttpMethod.GET,
        page_size=10,
        page_start=1,
        max_pages_limit=100,
        review_selector="",
        custom_extractor=None,
        raw_html_parser=extract_reviews_from_html,
        selenium_crawler=selenium_crawl_ctrip,
        field_mapping={},
    )
