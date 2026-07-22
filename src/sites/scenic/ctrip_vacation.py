"""
模块名称：携程旅游（Ctrip Vacation）网站适配器

功能说明：
    - 携程旅游产品评论页面适配器（vacations.ctrip.com）
    - 全程 Selenium 翻页 + DOM 解析
    - Cookie 统一使用携程登录态
    - 共享 DOM 提取和 URL 工具在 _ctrip_base.py
"""

import time
import logging

from src.sites.base import SiteAdapter, HttpMethod
from src.sites.scenic._ctrip_base import (
    extract_from_vacation_dom,
    extract_url_params,
    build_ctrip_url,
)

logger = logging.getLogger("tour-crawler.sites.ctrip")


# ==================== Selenium 翻页爬取（旅游） ====================

def selenium_crawl_ctrip_vacation(url: str, max_pages: int = 10,
                                  max_count: int = 0, timeout: int = 300,
                                  stop_check=None, progress_callback=None,
                                  cookie_file=None,
                                  filter_chain=None, task_name: str = "",
                                  driver_ref: list | None = None,
                                  notifier=None, resume_page: int = 0,
                                  resume_count: int = 0,
                                  delay_seconds: float = 2.0) -> tuple[list[dict], int]:
    _prefix = f"任务 [{task_name}] " if task_name else ""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
    except ImportError:
        logger.error(f"{_prefix}Selenium 未安装，无法翻页爬取")
        return [], 0

    options = Options()
    options.add_argument("--window-position=-32000,-32000")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    from src.engine.browser import create_edge_driver
    from src.sites.scenic._ctrip_base import inject_ctrip_cookies

    driver = create_edge_driver(options)
    if driver_ref is not None:
        driver_ref.append(driver)
    all_reviews = []
    total_rejected = 0

    try:
        # 注入 Cookie
        inject_ctrip_cookies(driver, cookie_file)

        # 构造干净 URL
        params = extract_url_params(url)
        clean_url = build_ctrip_url(
            params.get("domain", "vacations.ctrip.com"),
            params.get("id", ""),
            params.get("location", ""),
        )
        driver.get(clean_url)
        wait = WebDriverWait(driver, 15)

        # 断点续爬：快速翻到 resume_page
        start_page = resume_page if resume_page > 1 else 1
        if start_page > 1:
            logger.info(f"{_prefix}断点续爬：跳过前 {start_page - 1} 页，从第 {start_page} 页开始")
            for _ in range(1, start_page):
                if stop_check and stop_check():
                    break
                try:
                    next_btn = driver.find_element(
                        By.CSS_SELECTOR, '.ct-review-pagination-next:not(.ct-review-pagination-disabled)'
                    )
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(1)
                except NoSuchElementException:
                    logger.warning(f"{_prefix}断点续爬：无法翻到第 {start_page} 页，从当前位置开始")
                    break

        for page in range(start_page, max_pages + 1):
            if stop_check and stop_check():
                logger.info(f"{_prefix}Selenium 翻页被外部停止")
                break

            if max_count and len(all_reviews) >= max_count:
                logger.info(f"{_prefix}已达到目标条数 {max_count}，停止翻页")
                break

            page_start = time.time()

            try:
                wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, '.ct-review-list-item'))
            except TimeoutException:
                logger.warning(f"{_prefix}第 {page} 页等待评论加载超时")
                break

            time.sleep(1)

            html = driver.page_source
            page_reviews = extract_from_vacation_dom(html)

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
                    page_num=page, count=new_count, total=len(all_reviews),
                    message=f"正在爬取第 {page} 页...（累计 {len(all_reviews)} 条）"
                )

            if max_count and len(all_reviews) >= max_count:
                break

            if time.time() - page_start > timeout:
                logger.warning(f"{_prefix}第 {page} 页处理超时（{timeout}秒）")
                break

            if page < max_pages:
                try:
                    next_btn = driver.find_element(
                        By.CSS_SELECTOR, '.ct-review-pagination-next:not(.ct-review-pagination-disabled)'
                    )
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(1.5)
                except NoSuchElementException:
                    logger.info(f"{_prefix}已到末页，翻页结束")
                    break
            else:
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

def _validate_ctrip_vacation_url(url: str) -> tuple[bool, str]:
    """校验是否为有效的携程旅游产品 URL"""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return (False, "无法解析 URL")
    if "vacations.ctrip.com" in host:
        return (True, "")
    return (False, "仅支持 vacations.ctrip.com 的携程旅游评价页面")


# ==================== 适配器入口 ====================

def create_ctrip_vacation_adapter() -> SiteAdapter:
    """创建携程旅游适配器实例"""
    return SiteAdapter(
        site_name="ctrip_vacation",
        site_display_name="携程",
        crawl_type="scenic",
        domain=".ctrip.com",
        login_url="https://passport.ctrip.com/user/login",
        url_template="https://vacations.ctrip.com/travel/detail/p{id}.html",
        http_method=HttpMethod.GET,
        page_size=10,
        page_start=1,
        max_pages_limit=99999,
        review_selector="",
        custom_extractor=None,
        raw_html_parser=None,
        selenium_crawler=selenium_crawl_ctrip_vacation,
        url_validator=_validate_ctrip_vacation_url,
        field_mapping={},
        login_cookie_names=("cticket",),
        cookie_platform="ctrip",
    )
