"""
模块名称：大众点评（Dianping）网站适配器

功能说明：
    - 大众点评景点/商户评论页面的适配规则
    - 通过 Selenium 驱动浏览器获取评论（绕过 CSS+SVG 字体加密）
    - 支持自动翻页
    - 需要大众点评登录 Cookie

URL 格式：
    https://www.dianping.com/shop/{shop_id}/review_all
    https://www.dianping.com/shop/{shop_id}/review_all/p{page}

技术要点：
    - 大众点评使用 CSS + SVG 字体加密部分文字
    - Selenium 浏览器渲染后文字自动解密，从 DOM 直接提取
    - 页面无翻页时自动停止
"""

import re
import time
import logging
from urllib.parse import urlparse

from src.sites.base import SiteAdapter, HttpMethod
from src.models.review import EMPTY_REVIEW

logger = logging.getLogger("tour-crawler.sites.dianping")


# ==================== URL 工具 ====================

def extract_shop_id(url: str) -> str | None:
    """
    从大众点评 URL 中提取商户 ID。

    支持格式：
        - https://www.dianping.com/shop/H7MG8iQ5X9P2Lm3R
        - https://www.dianping.com/shop/518986/review_all
        - https://www.dianping.com/shop/G9n2K3rF8sL1mQ6w/review_all/p2

    Args:
        url: 大众点评商户页面 URL

    Returns:
        商户 ID 字符串，未匹配时返回 None
    """
    m = re.search(r'/shop/([^/\s?#]+)', url)
    if m:
        return m.group(1)
    return None


# ==================== DOM 提取 ====================

def _parse_rating_from_class(class_str: str) -> float:
    """
    从评分 span 的 class 属性中解析星级。

    大众点评评分 class 格式：sml-strXX
        - sml-str50 = 5.0 星
        - sml-str45 = 4.5 星
        - sml-str40 = 4.0 星

    Args:
        class_str: span 元素的 class 属性值

    Returns:
        星级评分（0~5）
    """
    if not class_str:
        return 0
    m = re.search(r'sml-str(\d+)', str(class_str))
    if m:
        return int(m.group(1)) / 10.0
    return 0


def _extract_review_from_element(item, driver) -> dict:
    """
    从单个评论 DOM 元素中提取标准字段。

    Args:
        item: Selenium WebElement（单条评论容器）
        driver: Selenium WebDriver（用于 JS 执行）

    Returns:
        标准评论字典
    """
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    review = EMPTY_REVIEW.copy()

    try:
        # --- 用户名 ---
        try:
            name_el = item.find_element(By.CSS_SELECTOR, ".dper-info a.name, .dper-info .name, a.name, .user-name")
            review["username"] = name_el.text.strip()
        except NoSuchElementException:
            pass

        # --- 评分 ---
        try:
            rank_el = item.find_element(By.CSS_SELECTOR, ".review-rank span[class*='sml-str'], .rank span[class*='sml-str']")
            class_attr = rank_el.get_attribute("class")
            review["rating"] = _parse_rating_from_class(class_attr)
        except NoSuchElementException:
            pass

        # 如果上面的方式没取到评分，尝试用 title 属性
        if review["rating"] == 0:
            try:
                rank_el = item.find_element(By.CSS_SELECTOR, "[title*='星']")
                title = rank_el.get_attribute("title") or ""
                m = re.search(r"(\d+[\._]?\d*)", title)
                if m:
                    review["rating"] = float(m.group(1).replace("_", "."))
            except NoSuchElementException:
                pass

        # --- 评论文本 ---
        try:
            content_el = item.find_element(By.CSS_SELECTOR, ".review-words, .desc, .review-content, .comment-content")
            review["content"] = content_el.text.strip()
        except NoSuchElementException:
            try:
                # 回退：尝试获取整个评论容器的文本
                content_el = item.find_element(By.CSS_SELECTOR, ".main-review")
                review["content"] = content_el.text.strip()
            except NoSuchElementException:
                pass

        # --- 时间 ---
        try:
            time_el = item.find_element(By.CSS_SELECTOR, ".time, .review-time, .comment-time")
            review["time"] = time_el.text.strip()
        except NoSuchElementException:
            pass

        # --- 用户等级 ---
        try:
            level_el = item.find_element(By.CSS_SELECTOR, ".user-level, .user-rank-rst, .member-level")
            review["user_level"] = level_el.text.strip()
        except NoSuchElementException:
            pass

        # --- IP 属地 ---
        try:
            ip_el = item.find_element(By.CSS_SELECTOR, ".address, .ip-location, .ipLocation")
            ip_text = ip_el.text.strip()
            ip_text = ip_text.replace("IP属地：", "").replace("IP属地:", "").replace("IP：", "").strip()
            if ip_text:
                review["ip_location"] = ip_text
        except NoSuchElementException:
            pass

        # --- 图片 ---
        try:
            img_els = item.find_elements(By.CSS_SELECTOR, ".review-pictures img, .photos img, .img-list img")
            img_urls = []
            for img in img_els:
                # 优先取 data-big / data-lazyload，其次 src
                src = img.get_attribute("data-big") or img.get_attribute("data-lazyload") or img.get_attribute("src") or ""
                if src and src.strip():
                    img_urls.append(src.strip())
            review["image_urls"] = img_urls
        except Exception:
            pass

    except Exception as e:
        logger.debug(f"提取单条评论异常: {e}")

    return review


def extract_reviews_from_page(driver) -> list[dict]:
    """
    从当前页面提取所有评论。

    Args:
        driver: Selenium WebDriver 实例

    Returns:
        标准评论列表
    """
    from selenium.webdriver.common.by import By

    items = []
    # 尝试多种选择器（新旧版页面兼容）
    for selector in [
        ".reviews-items > ul > li",
        ".main-review",
        ".comment-list > ul > li",
        ".review-list > div",
    ]:
        items = driver.find_elements(By.CSS_SELECTOR, selector)
        if items:
            logger.debug(f"使用选择器 '{selector}' 找到 {len(items)} 条评论")
            break

    if not items:
        logger.warning("未找到评论元素，尝试回退选择器")
        # 尝试更宽泛的选择器
        for selector in [
            "[class*='review'] li",
            ".reviews-items li",
        ]:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                logger.debug(f"回退选择器 '{selector}' 找到 {len(items)} 条")
                break

    reviews = [_extract_review_from_element(item, driver) for item in items]
    # 过滤掉完全没有内容的条目
    reviews = [r for r in reviews if r.get("content") or r.get("username")]
    return reviews


# ==================== Selenium 翻页爬取 ====================

def _dedup_reviews(reviews: list[dict]) -> list[dict]:
    """基于用户名+内容前80字+时间 去重"""
    seen = set()
    result = []
    for r in reviews:
        key = (r.get("username", ""), r.get("content", "")[:80], r.get("time", ""))
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def selenium_crawl_dianping(
    url: str,
    max_pages: int = 100,
    max_count: int = 0,
    timeout: int = 600,
    stop_check=None,
    progress_callback=None,
) -> list[dict]:
    """
    通过 Selenium 驱动 Edge 浏览器，翻页爬取大众点评评论。

    大众点评使用 CSS+SVG 字体加密，Selenium 渲染后文字自动解密。
    用户需提前通过 Cookie 管理器登录大众点评。

    Args:
        url: 大众点评商户页面 URL（自动跳转到 review_all）
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
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    # 额外反检测参数
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Edge(options=options)
    all_reviews = []
    start_time = time.time()

    # 构建评论列表页 URL
    parsed = urlparse(url)
    review_url = url.rstrip("/")
    if "/review_all" not in review_url:
        review_url = review_url + "/review_all"

    try:
        driver.get(review_url)
        wait = WebDriverWait(driver, 15)

        # 等待并检测是否有评论加载
        try:
            wait.until(lambda d: (
                d.find_elements(By.CSS_SELECTOR, ".reviews-items li, .main-review, .comment-list li")
            ))
        except TimeoutException:
            logger.warning("等待评论加载超时，页面可能需要登录或触发了验证")
            # 检查是否是登录页
            current_url = driver.current_url
            if "login" in current_url.lower() or "account" in current_url.lower():
                logger.error("页面跳转到登录页，请先获取 Cookie")
            return []

        time.sleep(1.5)  # 等待渲染完成

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

            # 滚动页面以触发懒加载
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

            # 提取当前页评论
            page_reviews = extract_reviews_from_page(driver)

            before = len(all_reviews)
            all_reviews.extend(page_reviews)
            # 截断到 max_count
            if max_count and len(all_reviews) > max_count:
                all_reviews = all_reviews[:max_count]
            all_reviews = _dedup_reviews(all_reviews)
            new_count = len(all_reviews) - before

            logger.info(f"第 {page} 页: 提取 {len(page_reviews)} 条（新增 {new_count} 条，累计 {len(all_reviews)} 条）")

            # 进度回调
            if progress_callback:
                progress_callback(
                    page_num=page,
                    count=new_count,
                    total=len(all_reviews),
                    message=f"正在爬取第 {page} 页...（累计 {len(all_reviews)} 条）"
                )

            # 检查是否已达到目标
            if max_count and len(all_reviews) >= max_count:
                break

            # 翻到下一页
            if page >= max_pages:
                break

            try:
                # 尝试点击"下一页"按钮
                next_selectors = [
                    ".Pages .NextPage:not(.disabled)",
                    ".pagination .next:not(.disabled)",
                    "a.NextPage:not(.disabled)",
                    ".ant-pagination-next:not(.ant-pagination-disabled)",
                    "a.next:not(.disabled)",
                    ".page-next a",
                ]
                next_btn = None
                for sel in next_selectors:
                    try:
                        next_btn = driver.find_element(By.CSS_SELECTOR, sel)
                        if next_btn.is_displayed() and next_btn.is_enabled():
                            break
                        next_btn = None
                    except NoSuchElementException:
                        continue

                if next_btn:
                    # 滚动到按钮可见
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                    time.sleep(0.5)
                    # 用 JS 点击避免元素被遮挡
                    driver.execute_script("arguments[0].click();", next_btn)
                    # 等待新评论加载
                    time.sleep(2)
                else:
                    logger.info("未找到下一页按钮，翻页结束")
                    break

            except Exception as e:
                logger.warning(f"翻页操作失败: {e}")
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

def create_dianping_adapter() -> SiteAdapter:
    """
    创建大众点评网适配器实例。

    使用 Selenium 浏览器渲染模式绕过 CSS 字体加密，
    从渲染后的 DOM 提取评论数据。

    Returns:
        配置完成的大众点评适配器
    """
    return SiteAdapter(
        site_name="dianping",
        site_display_name="大众点评",
        domain=".dianping.com",
        login_url="https://account.dianping.com/login",
        url_template="https://www.dianping.com/shop/{id}",

        http_method=HttpMethod.GET,

        page_size=20,
        page_start=1,
        max_pages_limit=100,

        review_selector="",
        custom_extractor=None,
        raw_html_parser=None,
        selenium_crawler=selenium_crawl_dianping,

        field_mapping={},
    )
