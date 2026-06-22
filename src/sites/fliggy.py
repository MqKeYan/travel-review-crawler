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
            review["image_urls"] = [img.get_attribute("src") for img in imgs if img.get_attribute("src")]
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
                img.get("src", "") for img in img_els if img.get("src")
            ]

        # --- 子评分（如果有的话，通常在 body 之前）---
        sub_score_els = item.select("[class*='score'], [class*='rating']")
        sub_scores = []
        for el in sub_score_els:
            txt = el.get_text(strip=True)
            if txt and len(txt) < 20:
                sub_scores.append(txt)
        if sub_scores:
            review["sub_scores"] = " | ".join(sub_scores)

        reviews.append(review)

    logger.info(f"飞猪 HTML 提取: {len(reviews)} 条评论")
    return reviews


# ==================== Selenium 翻页爬取 ====================

def _dedup_reviews(reviews: list[dict]) -> list[dict]:
    """基于用户名+内容前80字去重"""
    seen = set()
    result = []
    for r in reviews:
        key = (r.get("username", ""), r.get("content", "")[:80], r.get("time", ""))
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def selenium_crawl_fliggy(
    url: str,
    max_pages: int = 100,
    max_count: int = 0,
    timeout: int = 600,
    stop_check=None,
    progress_callback=None,
    cookie_file: str | None = None,
) -> list[dict]:
    """
    飞猪评论爬虫：
    1. 注入 Cookie 后访问页面
    2. 点击「全部评价」按钮展开评论面板
    3. 循环点击 #morecomments 加载更多评论
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    except ImportError:
        logger.error("Selenium 未安装")
        return []

    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    # 后台静默模式（不显示浏览器窗口）
    options.add_argument("--headless=new")

    driver = webdriver.Edge(options=options)
    all_reviews = []
    start_time = time.time()
    batch = 0

    try:
        # 注入 Cookie（飞猪需要登录态）
        if cookie_file:
            from src.engine.cookie_manager import load_cookies_from_file
            cookie_name = cookie_file.replace(".json", "")
            cookies = load_cookies_from_file("fliggy", cookie_name)
            if cookies:
                # 先访问目标域名才能注入 Cookie
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
                logger.info(f"飞猪: 已注入 {len(cookies)} 条 Cookie")

        driver.get(url)
        wait = WebDriverWait(driver, 20)
        time.sleep(2)

        # 检查登录跳转
        if "login" in driver.current_url.lower():
            logger.error("飞猪: 跳转到登录页，请先获取 Cookie")
            return []

        # 验证码检测：自动求解（后台模式最多重试5次）
        from src.engine.captcha_solver import solve_captcha_with_fallback, detect_slider_captcha
        captcha_result = solve_captcha_with_fallback(driver, progress_callback)
        if captcha_result == "manual_needed":
            logger.warning("飞猪: 后台模式自动求解失败，尝试额外重试...")
            # 后台模式无法手动操作，增加自动重试
            from src.engine.captcha_solver import solve_slider_captcha
            for extra_attempt in range(5):
                time.sleep(2)
                if not detect_slider_captcha(driver):
                    break
                logger.info(f"飞猪: 后台自动重试验证 ({extra_attempt+1}/5)...")
                if solve_slider_captcha(driver, max_attempts=1):
                    break
            else:
                if detect_slider_captcha(driver):
                    logger.error("飞猪: 后台模式无法通过验证码，放弃本次爬取")
                    return []
            time.sleep(2)

        # ---- 步骤1：滚动到评论区域，点击「全部评价」 ----
        # 先尝试直接跳到评论锚点
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        # 如果页面有评论锚点，直接定位
        try:
            comment_section = driver.find_element(By.CSS_SELECTOR, "#comment, .trip-pc-detail-comments")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_section)
            time.sleep(1)
        except NoSuchElementException:
            pass

        # 查找「全部评价」按钮
        btns = driver.find_elements(By.CSS_SELECTOR, ".trip-pc-detail-comments__show-more-btn")
        if not btns:
            btns = driver.find_elements(By.XPATH, "//*[contains(text(),'全部评价')]")
        if btns:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btns[0])
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btns[0])
                logger.info("飞猪: 已点击「全部评价」")
                time.sleep(3)
            except StaleElementReferenceException:
                logger.info("飞猪: 按钮已失效(页面已变化)，跳过点击")
        else:
            logger.info("飞猪: 未找到「全部评价」，尝试直接提取已有评论")

        # ---- 步骤2：在评论面板内滚动加载更多 ----
        # 找到评论面板的滚动容器
        scroll_container = None
        for sel in (".trip-pc-detail-comments--more-scroll", ".trip-pc-detail-comments-pad__body",
                     ".trip-pc-detail-comments-pad__wrap"):
            try:
                scroll_container = driver.find_element(By.CSS_SELECTOR, sel)
                logger.info(f"飞猪: 找到评论滚动容器 {sel}")
                break
            except NoSuchElementException:
                continue

        dry_count = 0
        seen_keys = set()
        while True:
            if stop_check and stop_check():
                break
            if time.time() - start_time > timeout:
                break

            # 检测验证码：自动求解（后台模式额外重试）
            if detect_slider_captcha(driver):
                logger.warning("飞猪: 爬取中再次遇到验证码，后台自动求解...")
                if progress_callback:
                    progress_callback(page_num=batch, count=0, total=len(all_reviews),
                                      message="再次遇到验证码，后台自动求解...")
                result = solve_captcha_with_fallback(driver, progress_callback)
                if result == "manual_needed":
                    from src.engine.captcha_solver import solve_slider_captcha
                    for extra_attempt in range(5):
                        time.sleep(2)
                        if not detect_slider_captcha(driver):
                            break
                        if solve_slider_captcha(driver, max_attempts=1):
                            break
                    else:
                        if detect_slider_captcha(driver):
                            logger.error("飞猪: 后台模式无法通过验证码，终止爬取")
                            break
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

            # 提取当前所有评论，仅保留新评论
            page_reviews = extract_fliggy_reviews_from_dom(driver)
            new_reviews = []
            for r in page_reviews:
                key = (r.get("username", ""), r.get("content", "")[:80], r.get("time", ""))
                if key not in seen_keys:
                    seen_keys.add(key)
                    new_reviews.append(r)

            before = len(all_reviews)
            all_reviews.extend(new_reviews)
            if max_count and len(all_reviews) > max_count:
                all_reviews = all_reviews[:max_count]
            new_count = len(all_reviews) - before

            batch += 1
            logger.info(f"飞猪 第{batch}批: 提取{len(page_reviews)}条 (新增{new_count}，累计{len(all_reviews)})")

            if progress_callback:
                progress_callback(
                    page_num=batch, count=new_count, total=len(all_reviews),
                    message=f"滚动加载中... (累计 {len(all_reviews)} 条)"
                )

            if max_count and len(all_reviews) >= max_count:
                break

            # 连续3次无新增且已滚动到底部则停止
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
        logger.error(f"飞猪异常: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

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
        domain=".fliggy.com",
        login_url="https://login.taobao.com/havanaone/login/login.htm",
        url_template="https://traveldetail.fliggy.com/item.htm?id={id}&pc=1",
        http_method=HttpMethod.GET,
        page_size=20,
        page_start=1,
        max_pages_limit=100,
        review_selector="",
        raw_html_parser=extract_fliggy_reviews,
        selenium_crawler=selenium_crawl_fliggy,
        field_mapping={},
    )
