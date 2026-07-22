"""
模块名称：飞猪（Fliggy）网站适配器

功能说明：
    - 飞猪旅游景点评论页面的适配规则
    - 通过 HTML 页面解析获取评论（rax-view-v2 组件渲染）
    - 通过点击「全部评价」按钮逐批加载全部评论

页面结构：
    飞猪景点评论页面由 Rax 框架渲染为 div.rax-view-v2 组件，
    每条评论为 .pcd-comment-one 容器，包含用户名、内容、日期、图片等。

URL 格式：
    https://travel.fliggy.com/detail?id={item_id}
"""

import re
import time
import logging

from src.sites.base import SiteAdapter, HttpMethod
from src.models.review import EMPTY_REVIEW
from src.utils.image_utils import extract_img_url_from_tag, extract_img_url_from_selenium

logger = logging.getLogger("tour-crawler.sites.fliggy")


# ==================== HTML DOM 提取 ====================

def extract_fliggy_reviews_from_dom(driver) -> list[dict]:
    """通过 Selenium 直接从 DOM 提取评论（绕过 BS4 解析问题）"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import StaleElementReferenceException
    items = driver.find_elements(By.CSS_SELECTOR, ".pcd-comment-one")
    if not items:
        logger.warning(f"飞猪 DOM: 未找到 .pcd-comment-one，尝试回退选择器")
        items = driver.find_elements(By.CSS_SELECTOR, "[class*='pcd-comment-one']")
    if not items:
        return []

    reviews = []
    for item in items:
        try:
            review = EMPTY_REVIEW.copy()
            review["username"] = item.find_element(By.CSS_SELECTOR, ".pcd-comment-one__nickname").text.strip()
            review["content"] = item.find_element(By.CSS_SELECTOR, ".pcd-comment-one__text").text.strip()
            date_text = item.find_element(By.CSS_SELECTOR, ".pcd-comment-one__date").text.strip()
            m = re.match(r"(\d{4}-\d{2}-\d{2})", date_text)
            if m:
                review["time"] = m.group(1)
            review["avatar_url"] = item.find_element(By.CSS_SELECTOR, ".pcd-comment-one__user-icon").get_attribute("src") or ""
            imgs = item.find_elements(By.CSS_SELECTOR, ".pcd-comment-one__image")
            review["image_urls"] = [extract_img_url_from_selenium(img) for img in imgs]
            reviews.append(review)
        except StaleElementReferenceException:
            continue
        except Exception:
            continue

    logger.info(f"飞猪 DOM: 提取 {len(reviews)} 条评论")
    return reviews


def extract_fliggy_reviews(html_text: str) -> list[dict]:
    """
    从飞猪 HTML 页面提取评论。

    Args:
        html_text: 页面 HTML 源码

    Returns:
        标准评论列表
    """
    from bs4 import BeautifulSoup

    # 先用 lxml，失败换 html.parser
    for parser_name in ("lxml", "html.parser"):
        try:
            soup = BeautifulSoup(html_text, parser_name)
        except Exception:
            continue
        items = soup.select(".pcd-comment-one")
        if not items:
            items = soup.select("[class*='pcd-comment-one']")
        if items:
            logger.info(f"飞猪: {parser_name} 找到 {len(items)} 条")
            break

    if not items:
        logger.warning(f"飞猪: 未找到评论，长度={len(html_text)}")
        return []

    reviews = []
    for item in items:
        review = EMPTY_REVIEW.copy()

        # --- 用户名 ---
        nickname_el = item.select_one(".pcd-comment-one__nickname")
        if nickname_el:
            review["username"] = nickname_el.get_text(strip=True)

        # --- 用户头像 ---
        icon_el = item.select_one(".pcd-comment-one__user-icon")
        if icon_el:
            review["avatar_url"] = icon_el.get("src", "")

        # --- 评论内容 ---
        text_el = item.select_one(".pcd-comment-one__text")
        if text_el:
            review["content"] = text_el.get_text(strip=True)

        # --- 日期 / 票种 ---
        date_el = item.select_one(".pcd-comment-one__date")
        if date_el:
            date_text = date_el.get_text(strip=True)
            m = re.match(r"(\d{4}-\d{2}-\d{2})", date_text)
            if m:
                review["time"] = m.group(1)

        # --- 图片 ---
        img_els = item.select(".pcd-comment-one__image")
        if img_els:
            review["image_urls"] = [
                extract_img_url_from_tag(img) for img in img_els
            ]

        reviews.append(review)

    logger.info(f"飞猪 HTML 提取: {len(reviews)} 条评论")
    return reviews


# ==================== URL 构造 ====================

def extract_url_params(url: str) -> dict[str, str]:
    """从飞猪商品 URL 中提取关键参数"""
    from urllib.parse import urlparse
    params = {}
    try:
        host = urlparse(url).netloc.lower()
        if "fliggy.com" in host:
            params["domain"] = "traveldetail.fliggy.com"
    except Exception:
        pass
    m = re.search(r'[?&]id=(\d+)', url)
    if m:
        params["id"] = m.group(1)
    return params


def build_fliggy_url(domain: str, id: str) -> str:
    """用提取的参数构造干净的飞猪商品页 URL"""
    return f"https://{domain}/item.htm?id={id}&pc=1"


# ==================== Selenium 翻页爬取 ====================

def selenium_crawl_fliggy(
    url: str,
    max_pages: int = 99999,
    max_count: int = 0,
    timeout: int = 600,
    stop_check=None,
    progress_callback=None,
    cookie_file: str | None = None,
    filter_chain=None,
    task_name: str = "",
    driver_ref: list | None = None,
    notifier=None,
    resume_page: int = 0,
    resume_count: int = 0,
    delay_seconds: float = 2.0,
) -> list[dict]:
    """
    飞猪评论爬虫（阿里系平台，使用最小化窗口 + 验证码通知）：
    1. 注入 Cookie 后访问页面
    2. 点击「全部评价」按钮展开评论面板
    3. 循环滚动加载评论，遇验证码通知用户手动处理
    """
    _prefix = f"任务 [{task_name}] " if task_name else ""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    except ImportError:
        logger.error(f"{_prefix}Selenium 未安装")
        return []

    options = Options()
    options.page_load_strategy = 'eager'  # DOM就绪即返回，不等所有资源加载完
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")

    from src.engine.browser import create_edge_driver_minimized

    driver = create_edge_driver_minimized(options)
    if driver_ref is not None:
        driver_ref.append(driver)
    all_reviews = []
    batch = 0

    try:
        # 注入 Cookie（飞猪需要登录态）
        if cookie_file:
            from src.engine.cookie_manager import load_cookies_from_file
            cookie_name = cookie_file.replace(".json", "")
            cookies = load_cookies_from_file("fliggy", cookie_name)
            if cookies:
                driver.get("https://www.fliggy.com")
                time.sleep(1)
                for c in cookies:
                    try:
                        driver.add_cookie({
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c.get("domain", ".fliggy.com"),
                            "path": c.get("path", "/"),
                        })
                    except Exception:
                        pass
                logger.info(f"{_prefix}飞猪: 已注入 {len(cookies)} 条 Cookie")

        # 构造干净 URL
        url_params = extract_url_params(url)
        clean_url = build_fliggy_url(
            url_params.get("domain", "traveldetail.fliggy.com"),
            url_params.get("id", ""),
        )
        driver.get(clean_url)
        wait = WebDriverWait(driver, 20)
        time.sleep(2)

        if "login" in driver.current_url.lower():
            logger.error(f"{_prefix}飞猪: 跳转到登录页，请先获取 Cookie")
            return []

        # 验证码检测：通知用户手动处理
        from src.engine.captcha_handler import detect_captcha, wait_for_captcha_solved
        if detect_captcha(driver):
            if not wait_for_captcha_solved(driver, notifier, task_name,
                                           progress_callback=progress_callback):
                logger.error(f"{_prefix}飞猪: 等待验证码超时，放弃本次爬取")
                return []
            time.sleep(2)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        try:
            comment_section = driver.find_element(By.CSS_SELECTOR, "#comment, .trip-pc-detail-comments")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_section)
            time.sleep(1)
        except NoSuchElementException:
            pass

        btns = driver.find_elements(By.CSS_SELECTOR, ".trip-pc-detail-comments__show-more-btn")
        if not btns:
            btns = driver.find_elements(By.XPATH, "//*[contains(text(),'全部评价')]")
        if btns:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btns[0])
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btns[0])
                logger.info(f"{_prefix}飞猪: 已点击「全部评价」")
                time.sleep(3)
            except StaleElementReferenceException:
                logger.info(f"{_prefix}飞猪: 按钮已失效(页面已变化)，跳过点击")
        else:
            logger.info(f"{_prefix}飞猪: 未找到「全部评价」，尝试直接提取已有评论")

        # ---- 在评论面板内滚动加载更多 ----
        scroll_container = None
        for sel in (".trip-pc-detail-comments--more-scroll", ".trip-pc-detail-comments-pad__body",
                     ".trip-pc-detail-comments-pad__wrap"):
            try:
                scroll_container = driver.find_element(By.CSS_SELECTOR, sel)
                logger.info(f"{_prefix}飞猪: 找到评论滚动容器 {sel}")
                break
            except NoSuchElementException:
                continue

        dry_count = 0
        seen_keys = set()
        skipped_count = 0  # 断点续爬：已跳过的评论数

        # 断点续爬提示
        if resume_count > 0:
            logger.info(f"{_prefix}飞猪: 断点续爬，跳过前 {resume_count} 条已收集评论")

        while True:
            if stop_check and stop_check():
                break

            batch_start = time.time()

            # 验证码检测 → 通知用户手动处理（不重建 driver，等待通过后继续）
            if detect_captcha(driver):
                logger.warning(f"{_prefix}飞猪: 爬取中遇到验证码，通知用户手动处理...")
                if not wait_for_captcha_solved(driver, notifier, task_name,
                                               progress_callback=progress_callback):
                    logger.error(f"{_prefix}飞猪: 等待验证码超时，终止爬取")
                    break
                # 验证码通过后刷新等待，确保页面恢复正常
                wait = WebDriverWait(driver, 20)
                time.sleep(2)
                continue

            # 在评论面板内向下滚动触发自动加载
            if scroll_container:
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollTop + 1200;", scroll_container
                )
            else:
                driver.execute_script("window.scrollBy(0, 1200);")
            time.sleep(2)

            # 提取当前所有评论，仅保留新评论（断点续爬跳过前 resume_count 条）
            page_reviews = extract_fliggy_reviews_from_dom(driver)
            new_reviews = []
            for r in page_reviews:
                key = (r.get("username", ""), r.get("content", ""), r.get("time", ""))
                if key not in seen_keys:
                    seen_keys.add(key)
                    if skipped_count < resume_count:
                        skipped_count += 1
                        continue  # 跳过已爬过的评论
                    new_reviews.append(r)

            before = len(all_reviews)
            all_reviews.extend(new_reviews)
            if max_count and len(all_reviews) > max_count:
                all_reviews = all_reviews[:max_count]
            new_count = len(all_reviews) - before
            total_display = resume_count + len(all_reviews)  # 含已爬过的总数

            batch += 1
            logger.info(f"{_prefix}飞猪 第{batch}批: 提取{len(page_reviews)}条 (新增{new_count}，累计{total_display})")

            if progress_callback:
                progress_callback(
                    page_num=batch, count=new_count, total=total_display,
                    message=f"滚动加载中... (累计 {total_display} 条)"
                )

            if max_count and len(all_reviews) >= max_count:
                break

            if time.time() - batch_start > timeout:
                logger.warning(f"第{batch+1}批处理超时（{timeout}秒）")
                break

            if new_count == 0:
                dry_count += 1
                if scroll_container:
                    at_bottom = driver.execute_script(
                        "var c=arguments[0]; return c.scrollTop + c.clientHeight >= c.scrollHeight - 50;",
                        scroll_container
                    )
                else:
                    at_bottom = driver.execute_script(
                        "return window.innerHeight + window.scrollY >= document.body.scrollHeight - 100;"
                    )
                if dry_count >= 4 and at_bottom:
                    logger.info("飞猪: 已到底部且无新增，加载完毕")
                    break
            else:
                dry_count = 0

    except Exception as e:
        logger.error(f"{_prefix}飞猪异常: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        if driver_ref is not None:
            driver_ref.clear()

    return all_reviews


# ==================== 适配器入口 ====================

def create_fliggy_adapter() -> SiteAdapter:
    """
    创建飞猪网适配器实例。

    飞猪使用 Rax 框架渲染，无传统分页，评论通过「全部评价」按钮逐批加载。
    Selenium 自动点击按钮直到全部评论加载完毕，再从 DOM 提取。

    Returns:
        配置完成的飞猪适配器
    """
    return SiteAdapter(
        site_name="fliggy",
        site_display_name="飞猪",
        crawl_type="scenic",
        domain=".fliggy.com",
        login_url="https://login.taobao.com/havanaone/login/login.htm",
        url_template="https://traveldetail.fliggy.com/item.htm?id={id}&pc=1",
        http_method=HttpMethod.GET,
        page_size=20,
        page_start=1,
        max_pages_limit=99999,
        review_selector="",
        raw_html_parser=extract_fliggy_reviews,
        selenium_crawler=selenium_crawl_fliggy,
        field_mapping={},
        login_cookie_names=("login_uid", "S_token", "dper", "unb", "cookie2"),
    )
