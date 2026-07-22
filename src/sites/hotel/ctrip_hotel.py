"""
模块名称：携程酒店（Ctrip Hotel）网站适配器

功能说明：
    - 携程酒店评论页面的适配规则
    - 通过 Selenium 驱动浏览器：切换点评标签 → 排序最近入住 → 展开更多 → 翻页提取
    - 需要携程登录 Cookie

URL 格式：
    https://hotels.ctrip.com/hotels/ID.html
"""

import re
import time
import logging

from src.sites.base import SiteAdapter, HttpMethod
from src.models.review import EMPTY_REVIEW
from src.utils.image_utils import extract_img_url_from_tag

logger = logging.getLogger("tour-crawler.sites.ctrip_hotel")


# ==================== URL 工具 ====================

def extract_hotel_id(url: str) -> str | None:
    """从携程酒店 URL 中提取酒店 ID"""
    m = re.search(r'/hotels/(\d+)', url)
    if m:
        return m.group(1)
    return None


# ==================== DOM 提取 ====================

def _extract_review_from_element(item) -> dict:
    """从单个酒店评论 DOM 元素中提取标准字段"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    review = EMPTY_REVIEW.copy()

    try:
        # --- 用户名 ---
        try:
            name_el = item.find_element(By.CSS_SELECTOR, ".yCIHzFRsP6Tzk7Kia6Qo")
            review["username"] = name_el.text.strip()
        except NoSuchElementException:
            pass

        # --- 评分 ---
        try:
            score_el = item.find_element(By.CSS_SELECTOR, ".xt_R_A70sdDRsOgExJWw")
            score_text = score_el.text.strip()
            review["rating"] = float(score_text) if score_text else 0
        except NoSuchElementException:
            pass

        # --- 评论文本 ---
        try:
            content_el = item.find_element(By.CSS_SELECTOR, ".tpHRPkB7n9UV_c7A5t6h")
            review["content"] = content_el.text.strip()
        except NoSuchElementException:
            pass

        # --- 时间 ---
        try:
            time_el = item.find_element(By.CSS_SELECTOR, ".nUgIw0PM47FsRYfjswPo, .LPPTO8g2RH0Fk19jYMOQ")
            review["time"] = time_el.text.strip()
        except NoSuchElementException:
            pass

        # --- 房型 ---
        try:
            room_el = item.find_element(By.CSS_SELECTOR, ".HtVa6_VosW_fPAorAvVD")
            # 取第一个（房型），跳过入住日期等
            review["room_type"] = room_el.text.strip()
        except NoSuchElementException:
            pass

        # --- 图片 ---
        try:
            img_els = item.find_elements(By.CSS_SELECTOR, ".ftTBW8GGRjYIcn8xuaiY")
            img_urls = []
            for img in img_els:
                src = img.get_attribute("src") or ""
                if src and src.strip():
                    img_urls.append(src.strip())
            review["image_urls"] = img_urls
        except Exception:
            pass

        # --- 酒店回复 ---
        try:
            reply_el = item.find_element(By.CSS_SELECTOR, ".qUERH0dj6c94FltfokWY .sUdWKlPllhsIdSuv4Fk5")
            reply_text = reply_el.text.strip()
            if reply_text:
                review["reply"] = reply_text
        except NoSuchElementException:
            pass

    except Exception as e:
        logger.debug(f"提取酒店评论异常: {e}")

    return review


def extract_reviews_from_page(driver) -> list[dict]:
    """从当前页面提取所有酒店评论"""
    from selenium.webdriver.common.by import By

    items = driver.find_elements(By.CSS_SELECTOR, ".yRvZgc0SICPUbmdb2L2a")
    if not items:
        logger.warning("未找到酒店评论元素")
        return []

    reviews = [_extract_review_from_element(item) for item in items]
    reviews = [r for r in reviews if r.get("content")]
    return reviews


# ==================== 页面预处理 ====================

def _click_review_tab(driver) -> bool:
    """点击「点评」标签页"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    try:
        # role="tab" 精确匹配可点击的点评标签，避免与其他含"点评"的元素冲突
        tab = driver.find_element(By.CSS_SELECTOR, "[role=\"tab\"][aria-label=\"点评\"]")
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(2)
        logger.info(f"{_prefix}已点击「点评」标签")
        return True
    except NoSuchElementException:
        logger.info(f"{_prefix}未找到「点评」标签，将尝试「展开更多」")
        return False


def _set_sort_recent(driver) -> bool:
    """设置排序方式为「最近入住」"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

    try:
        # 找到排序下拉框并点击展开
        sort_dropdown = driver.find_element(By.CSS_SELECTOR, ".V9h6mggmjkh9TP4RQKyd .gEdAY0hpenkKEuXxkokx")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_dropdown)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", sort_dropdown)
        time.sleep(1)
        # 点击「最近入住」选项
        recent_opt = driver.find_element(By.CSS_SELECTOR, ".V9h6mggmjkh9TP4RQKyd .ceOnXE_xI6aGRTgG_wCS:nth-child(2)")
        driver.execute_script("arguments[0].click();", recent_opt)
        time.sleep(2)
        logger.info(f"{_prefix}已设置排序为「最近入住」")
        return True
    except (NoSuchElementException, ElementClickInterceptedException):
        logger.info(f"{_prefix}设置排序方式失败，使用默认排序")
        return False


def _click_expand_button(driver) -> bool:
    """点击「展开更多」按钮加载评论列表"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

    try:
        btn = driver.find_element(By.ID, "review-swiper-show-more-button")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
        logger.info(f"{_prefix}已点击「展开更多」按钮")
        return True
    except NoSuchElementException:
        logger.info(f"{_prefix}未找到「展开更多」按钮，评论可能已直接加载")
        return False
    except ElementClickInterceptedException:
        try:
            btn = driver.find_element(By.ID, "review-swiper-show-more-button")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return True
        except Exception:
            return False


def _click_next_page(driver) -> bool:
    """点击下一页按钮"""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException

    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, ".KtjTmkGBZvROMSO8zK_Q .pQoxbX5l0DdjPttuVUQx")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)
        return True
    except NoSuchElementException:
        return False


def selenium_crawl_ctrip_hotel(
    url: str,
    max_pages: int = 99999,
    max_count: int = 0,
    timeout: int = 600,
    stop_check=None,
    progress_callback=None,
    cookie_file=None,
    filter_chain=None,
    task_name: str = "",
    driver_ref: list | None = None,
    notifier=None,
    resume_page: int = 0,
    resume_count: int = 0,
    delay_seconds: float = 2.0,
) -> tuple[list[dict], int]:
    """通过 Selenium 翻页爬取携程酒店评论"""
    _prefix = f"任务 [{task_name}] " if task_name else ""
    try:
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        logger.error(f"{_prefix}Selenium 未安装")
        return [], 0

    options = Options()
    options.add_argument("--window-position=-32000,-32000")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-sandbox")

    from src.engine.browser import create_edge_driver
    from src.sites.scenic._ctrip_base import inject_ctrip_cookies

    driver = create_edge_driver(options)
    if driver_ref is not None:
        driver_ref.append(driver)
    all_reviews = []
    total_rejected = 0

    try:
        # 注入 Cookie（统一从 ctrip 目录读取）
        inject_ctrip_cookies(driver, cookie_file)

        # 构造干净 URL
        params = extract_url_params(url)
        clean_url = build_ctrip_hotel_url(
            params.get("domain", "hotels.ctrip.com"),
            params.get("id", ""),
        )
        driver.get(clean_url)
        wait = WebDriverWait(driver, 15)
        time.sleep(3)

        # 预处理：点击「点评」标签加载评论（失败则回退到「展开更多」）
        if not _click_review_tab(driver):
            _click_expand_button(driver)
        _set_sort_recent(driver)

        # 等待评论加载
        try:
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".yRvZgc0SICPUbmdb2L2a"))
        except Exception:
            logger.warning(f"{_prefix}等待酒店评论加载超时")

        # 断点续爬：快速翻到 resume_page
        start_page = resume_page if resume_page > 1 else 1
        if start_page > 1:
            logger.info(f"{_prefix}断点续爬：跳过前 {start_page - 1} 页，从第 {start_page} 页开始")
            for _ in range(1, start_page):
                if stop_check and stop_check():
                    break
                try:
                    if not _click_next_page(driver):
                        logger.warning(f"{_prefix}断点续爬：无法翻到第 {start_page} 页，从当前位置开始")
                        break
                    time.sleep(0.5)
                except Exception:
                    logger.warning(f"{_prefix}断点续爬：翻页异常，从当前位置开始")
                    break

        for page in range(start_page, max_pages + 1):
            if stop_check and stop_check():
                logger.info(f"{_prefix}Selenium 翻页被外部停止")
                break

            if max_count and len(all_reviews) >= max_count:
                logger.info(f"{_prefix}已达到目标条数 {max_count}，停止翻页")
                break

            page_start = time.time()

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

            page_reviews = extract_reviews_from_page(driver)

            # 逐页过滤
            raw_count = len(page_reviews)
            if filter_chain and page_reviews:
                page_reviews, rejected_batch = filter_chain.apply(page_reviews)
                total_rejected += len(rejected_batch)

            before = len(all_reviews)
            all_reviews.extend(page_reviews)
            if max_count and len(all_reviews) > max_count:
                overflow = len(all_reviews) - max_count
                all_reviews = all_reviews[:max_count]
                total_rejected += overflow
            new_count = len(all_reviews) - before

            if filter_chain:
                logger.info(f"{_prefix}第 {page} 页: 提取 {raw_count} 条 → 过滤后 {len(page_reviews)} 条（累计通过 {len(all_reviews)} 条, 过滤 {total_rejected} 条）")
            else:
                logger.info(f"{_prefix}第 {page} 页: 提取 {raw_count} 条（新增 {new_count} 条，累计 {len(all_reviews)} 条）")

            if progress_callback:
                progress_callback(
                    page_num=page,
                    count=new_count,
                    total=len(all_reviews),
                    message=f"正在爬取第 {page} 页...（累计 {len(all_reviews)} 条）"
                )

            if max_count and len(all_reviews) >= max_count:
                break

            if time.time() - page_start > timeout:
                logger.warning(f"{_prefix}第 {page} 页处理超时（{timeout}秒）")
                break

            if page >= max_pages:
                break

            if not _click_next_page(driver):
                logger.info(f"{_prefix}未找到下一页按钮，翻页结束")
                break

    except Exception as e:
        logger.error(f"{_prefix}Selenium 翻页异常: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        if driver_ref is not None:
            driver_ref.clear()

    return all_reviews, total_rejected


# ==================== URL 校验 ====================

def _validate_ctrip_hotel_url(url: str) -> tuple[bool, str]:
    """校验是否为有效的携程酒店 URL"""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return (False, "无法解析 URL")
    if "hotels.ctrip.com" not in host:
        return (False, "仅支持 hotels.ctrip.com 的酒店评价页面")
    return (True, "")


# ==================== URL 构造 ====================

def extract_url_params(url: str) -> dict[str, str]:
    """从携程酒店 URL 中提取关键参数（域名+酒店ID）"""
    from urllib.parse import urlparse
    params = {"domain": "hotels.ctrip.com"}
    rid = extract_hotel_id(url)
    if rid:
        params["id"] = rid
    return params


def build_ctrip_hotel_url(domain: str, id: str) -> str:
    """用提取的参数构造干净的携程酒店 URL"""
    return f"https://{domain}/hotels/{id}.html"


# ==================== 适配器入口 ====================

def create_ctrip_hotel_adapter() -> SiteAdapter:
    """创建携程酒店适配器实例"""
    return SiteAdapter(
        site_name="ctrip_hotel",
        site_display_name="携程",
        crawl_type="hotel",
        domain=".ctrip.com",
        login_url="https://passport.ctrip.com/user/login",
        url_template="https://hotels.ctrip.com/hotels/{id}.html",
        http_method=HttpMethod.GET,
        page_size=20,
        page_start=1,
        max_pages_limit=99999,
        review_selector="",
        raw_html_parser=None,
        selenium_crawler=selenium_crawl_ctrip_hotel,
        url_validator=_validate_ctrip_hotel_url,
        field_mapping={},
        login_cookie_names=("cticket",),
        cookie_platform="ctrip",
    )
