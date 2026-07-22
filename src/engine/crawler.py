"""
模块名称：通用爬虫引擎

功能说明：
    - 基于 requests.Session 的通用爬虫核心
    - 支持 HTML 页面解析（BeautifulSoup + lxml）和 JSON API 解析
    - 自动分页、随机 UA、请求延迟、失败重试
    - Cookie 注入（从已保存的文件读取）
    - 反爬策略：随机 UA、随机延迟、Referer 链、自适应降速
    - 验证码检测和 Cookie 过期检测

依赖模块：
    - requests (第三方)
    - beautifulsoup4, lxml (第三方)
    - time, random, logging (标准库)
    - src.engine.ua_spoofer: get_random_headers, get_headers_for_api
    - src.engine.cookie_manager: load_cookies_from_file
    - src.sites.base: SiteAdapter, RequestType, parse_response
    - src.utils.exceptions: NetworkError, ParseError, RateLimitError, ...
    - src.filters.base: FilterChain
"""

import time
import random
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.engine.ua_spoofer import get_random_headers
from src.engine.cookie_manager import load_cookies_from_file
from src.sites.base import SiteAdapter, parse_response, extract_resource_id
from src.utils.exceptions import (
    NetworkError,
    ParseError,
    RateLimitError,
    CookieExpiredError,
    CaptchaDetectedError,
    CrawlError,
)

logger = logging.getLogger("tour-crawler.crawler")


# ==================== 爬虫常量 ====================
DEFAULT_TIMEOUT = 30            # HTTP 请求超时时间（秒）
MAX_RETRY_COUNT = 3             # 单页最大重试次数
RETRY_BACKOFF_BASE = 1.0        # 重试退避基数（秒）：1s → 3s → 9s
MIN_DELAY = 0.5                 # 请求间最小随机延迟（秒）
MAX_DELAY = 5.0                 # 请求间最大随机延迟（秒）
SLOW_DOWN_DELAY = 30.0          # 触发反爬后自适应降速的最大延迟（秒）
RATE_LIMIT_STATUS_CODES = {429}  # 限流状态码
CAPTCHA_KEYWORDS = [
    "验证码", "captcha", "verify", "安全验证",
    "请输入验证码", "人机验证",
]
LOGIN_REDIRECT_KEYWORDS = [
    "login", "signin", "passport", "account/login",
]


def _create_session(cookie_file: str | None = None, site: str = "") -> requests.Session:
    """
    创建并配置 requests.Session。

    为 Session 配置连接池、重试策略，并可选注入 Cookie。

    Args:
        cookie_file: Cookie 文件名（不含路径，如 "my_account"），
                     None 或空字符串表示不注入 Cookie
        site: 平台标识（如 "ctrip"），用于定位 Cookie 存放目录

    Returns:
        配置好的 Session 实例
    """
    session = requests.Session()

    # 配置连接池和重试策略：最多重试 2 次，对 500/502/503/504 状态码重试
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 注入 Cookie
    if cookie_file and site:
        # cookie_file 为纯文件名（不含 .json），site 为平台标识
        cookie_name = cookie_file.replace(".json", "")
        cookies = load_cookies_from_file(site, cookie_name)
        if cookies:
            for c in cookies:
                session.cookies.set(
                    c["name"], c["value"],
                    domain=c.get("domain", ""),
                    path=c.get("path", "/"),
                )

    return session


def _detect_captcha(response: requests.Response) -> bool:
    """
    检测响应中是否包含验证码特征。

    检查响应文本中的验证码关键词和页面标题。

    Args:
        response: HTTP 响应对象

    Returns:
        True 表示检测到验证码需要人工处理
    """
    text = response.text.lower()
    url = response.url.lower()

    # 检查响应文本中的验证码关键词
    for keyword in CAPTCHA_KEYWORDS:
        if keyword.lower() in text:
            return True

    # 检查 URL 是否跳转到验证页面
    if "captcha" in url or "verify" in url:
        return True

    return False


def _detect_cookie_expired(response: requests.Response, adapter: SiteAdapter) -> bool:
    """
    检测 Cookie 是否过期。

    判断依据：
    1. 响应状态码 302 且 Location 跳转到登录页
    2. 响应文本包含登录页面特征

    Args:
        response: HTTP 响应对象
        adapter: 网站适配器

    Returns:
        True 表示 Cookie 已过期或失效
    """
    # 检查 302 重定向到登录页
    if response.status_code == 302:
        location = response.headers.get("Location", "").lower()
        for keyword in LOGIN_REDIRECT_KEYWORDS:
            if keyword in location:
                return True

    # 检查响应 URL 是否跳转到登录页
    current_url = response.url.lower()
    if adapter.login_url and adapter.login_url.lower() in current_url:
        return True

    return False


def _check_rate_limit(response: requests.Response) -> bool:
    """检测是否触发了请求频率限制"""
    if response.status_code in RATE_LIMIT_STATUS_CODES:
        return True
    # 某些网站返回 200 但在响应体中包含限流信息
    if response.status_code == 403:
        text = response.text.lower()
        if "rate limit" in text or "too many" in text or "frequency" in text:
            return True
    return False


def _make_request(
    session: requests.Session,
    adapter: SiteAdapter,
    page_num: int,
    referer: str | None = None,
    extra_headers: dict | None = None,
    target_url: str | None = None,
) -> requests.Response:
    """
    发送单次 HTTP 请求。

    Args:
        session: 已配置的 requests.Session
        adapter: 网站适配器
        page_num: 当前页码
        referer: Referer 请求头
        extra_headers: 额外的请求头
        target_url: 目标页面 URL

    Returns:
        HTTP 响应对象
    """
    headers = get_random_headers()

    if referer:
        headers["Referer"] = referer

    if extra_headers:
        headers.update(extra_headers)

    url = target_url or ""

    response = session.request(
        method=adapter.http_method.name,
        url=url,
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    return response


def _wait_with_adaptive_delay(consecutive_errors: int) -> None:
    """
    自适应等待延迟。

    请求成功后使用正常延迟（0.5~5s），
    连续失败时逐步增加延迟至最高 30s。

    Args:
        consecutive_errors: 连续失败次数
    """
    if consecutive_errors == 0:
        # 正常请求间隔：0.5~5 秒随机
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
    else:
        # 连续失败时，逐步增大延迟
        delay = min(
            SLOW_DOWN_DELAY,
            random.uniform(MAX_DELAY, MAX_DELAY * (consecutive_errors + 1))
        )
    time.sleep(delay)


def crawl_single_page(
    session: requests.Session,
    adapter: SiteAdapter,
    page_num: int,
    referer: str | None = None,
    target_url: str | None = None,
    stop_check=None,
) -> tuple[list[dict], bool]:
    """
    爬取单页评论数据。

    自动根据适配器配置选择 HTML 解析或 JSON API 解析路径。
    带重试机制，失败时按指数退避策略重试。

    Args:
        session: 已注入 Cookie 的 requests.Session
        adapter: 目标网站的适配器配置
        page_num: 当前页码
        referer: Referer 请求头

    Returns:
        (评论列表, 是否还有更多页面) 元组
        - 评论列表为空时表示该页无数据（可能已到末页）
        - has_more 为 False 时爬虫应停止翻页

    Raises:
        NetworkError: 网络请求失败（重试耗尽后）
        ParseError: 页面解析失败
        RateLimitError: 触发请求频率限制
        CookieExpiredError: Cookie 已过期
        CaptchaDetectedError: 检测到验证码
    """
    last_error = None

    for attempt in range(MAX_RETRY_COUNT):
        # 重试前检查停止标志
        if stop_check and stop_check():
            logger.info(f"{_prefix}第 {page_num} 页爬取被外部停止")
            return [], False

        try:
            response = _make_request(session, adapter, page_num, referer, target_url=target_url)
        except requests.RequestException as e:
            last_error = e
            if attempt < MAX_RETRY_COUNT - 1:
                # 指数退避：1s → 3s → 9s
                delay = RETRY_BACKOFF_BASE * (3 ** attempt)
                logger.warning(
                    f"{_prefix}第 {page_num} 页请求失败（第{attempt+1}次/共{MAX_RETRY_COUNT}次）"
                    f"，{delay:.0f}s 后重试: {e}"
                )
                time.sleep(delay)
                continue
            raise NetworkError(f"第 {page_num} 页请求失败，已重试 {MAX_RETRY_COUNT} 次") from last_error

        # ---- 检测反爬和异常 ----
        if _check_rate_limit(response):
            raise RateLimitError(f"触发请求频率限制（状态码 {response.status_code}）")

        if response.status_code == 403 and _detect_captcha(response):
            raise CaptchaDetectedError("检测到验证码，需要人工验证")

        if _detect_cookie_expired(response, adapter):
            raise CookieExpiredError("Cookie 已过期，请重新获取")

        # ---- 解析响应 ----
        if response.status_code != 200:
            logger.warning(f"{_prefix}第 {page_num} 页返回非 200 状态码: {response.status_code}")
            return [], False

        try:
            reviews = parse_response(response, adapter)
        except Exception as e:
            raise ParseError(f"第 {page_num} 页解析失败: {e}") from e

        # 判断是否有更多页面：返回的评论数少于 page_size 时视为末页
        has_more = len(reviews) >= adapter.page_size

        return reviews, has_more

    # 不应到达此处（重试耗尽时会抛出异常）
    return [], False


def crawl_all_pages(
    adapter: SiteAdapter,
    cookie_file: str | None = None,
    max_pages: int | None = None,
    max_count: int | None = None,
    progress_callback=None,
    stop_check=None,
    target_url: str | None = None,
    delay_seconds: float = 2.0,
    filter_chain=None,
    task_name: str = "",
    driver_ref: list | None = None,
    notifier=None,
    resume_page: int = 0,
    resume_count: int = 0,
) -> tuple[list[dict], int]:
    """
    爬取指定网站的全部评论数据（多页自动翻页）。

    如果适配器设置了 selenium_crawler，则使用 Selenium 翻页爬取。
    否则使用常规的 requests 请求 + 翻页。

    过滤在爬取过程中逐页执行（而非爬完后再统一过滤），
    进度回调报告的 count/total 均为过滤后通过的数量。

    Args:
        adapter: 网站适配器
        cookie_file: Cookie 文件名
        max_pages: 最大翻页数限制，None 表示使用适配器的默认值
        max_count: 最大条数限制（过滤后条数），达到后停止
        progress_callback: 进度回调函数，接收 (page_num, count, total) 参数
                           count/total 均为过滤后通过的数量
        stop_check: 停止检测函数，返回 True 时停止爬取
        target_url: 目标页面 URL（用户输入），用作请求 Referer 和 HTML 模式的请求地址
        filter_chain: 过滤器责任链，None 表示不过滤
        resume_page: 断点续爬起始页码，0 表示从头开始
        resume_count: 断点续爬已有条数，Selenium 滚动模式用于跳过已收集评论

    Returns:
        (通过过滤的评论列表, 被过滤掉的条数) 元组
    """
    page_limit = max_pages or adapter.max_pages_limit
    total_rejected = 0
    _prefix = f"任务 [{task_name}] " if task_name else ""

    def _apply_filters(reviews: list[dict]) -> tuple[list[dict], int]:
        """对一批评论应用过滤器链，返回 (通过列表, 拒绝条数)"""
        if filter_chain is None or not reviews:
            return reviews, 0
        passed, rejected = filter_chain.apply(reviews)
        return passed, len(rejected)

    # ---- Selenium 翻页模式（需要 JS 渲染的网站） ----
    if adapter.selenium_crawler and target_url and page_limit > 1:
        if progress_callback:
            progress_callback(page_num=1, count=0, total=0, message="启动浏览器...")

        try:
            # 尝试传递 filter_chain（携程已支持逐页过滤）
            try:
                raw_reviews = adapter.selenium_crawler(
                    url=target_url,
                    max_pages=page_limit,
                    max_count=max_count or 0,
                    timeout=600,
                    stop_check=stop_check,
                    progress_callback=progress_callback,
                    cookie_file=cookie_file,
                    filter_chain=filter_chain,
                    task_name=task_name,
                    driver_ref=driver_ref,
                    notifier=notifier,
                    resume_page=resume_page,
                    resume_count=resume_count,
                    delay_seconds=delay_seconds,
                )
            except TypeError:
                # 旧版 selenium_crawler 不支持 filter_chain/driver_ref/notifier
                raw_reviews = adapter.selenium_crawler(
                    url=target_url,
                    max_pages=page_limit,
                    max_count=max_count or 0,
                    timeout=600,
                    stop_check=stop_check,
                    progress_callback=progress_callback,
                    cookie_file=cookie_file,
                    task_name=task_name,
                )
        except Exception as e:
            logger.error(f"{_prefix}Selenium 翻页失败: {e}")
            raw_reviews = [], 0

        # 处理返回值：新版返回 (list, int)，旧版返回 list
        if isinstance(raw_reviews, tuple):
            passed_reviews, rejected = raw_reviews
        else:
            passed_reviews, rejected = _apply_filters(raw_reviews)
        total_rejected += rejected

        total = len(passed_reviews)
        if progress_callback:
            progress_callback(page_num=1, count=total, total=total,
                            message=f"爬取完成: 通过 {total} 条, 过滤 {total_rejected} 条")
        logger.info(f"{_prefix}Selenium 爬取完成，共 {total} 条（过滤掉 {total_rejected} 条）")
        return passed_reviews, total_rejected

    # ---- 常规 requests 翻页模式 ----
    session = _create_session(cookie_file, site=adapter.site_name)
    all_reviews: list[dict] = []
    consecutive_errors = 0

    page_limit = max_pages or adapter.max_pages_limit
    referer = target_url

    # 断点续爬：优先使用 resume_page，否则从适配器起始页开始
    start_page = resume_page if resume_page > 0 else adapter.page_start

    for page_num in range(start_page, start_page + page_limit):
        # 检查外部停止请求
        if stop_check and stop_check():
            logger.info(f"{_prefix}爬取任务被外部停止")
            break

        # 检查是否已达到目标条数（过滤后条数）
        if max_count and len(all_reviews) >= max_count:
            break

        try:
            raw_reviews, has_more = crawl_single_page(
                session, adapter, page_num, referer, target_url, stop_check
            )

            consecutive_errors = 0  # 成功，重置连续失败计数

            # ---- 逐页过滤：在爬取过程中立即过滤 ----
            page_passed_count = 0
            if raw_reviews:
                passed, rejected = _apply_filters(raw_reviews)
                total_rejected += rejected
                all_reviews.extend(passed)
                page_passed_count = len(passed)

                # 达到 max_count 时截断多余数据（过滤后条数）
                if max_count and len(all_reviews) > max_count:
                    overflow = len(all_reviews) - max_count
                    total_rejected += overflow  # 溢出的也算被过滤
                    all_reviews = all_reviews[:max_count]
                    page_passed_count -= overflow

                if filter_chain:
                    logger.info(
                        f"{_prefix}第 {page_num} 页完成: 解析 {len(raw_reviews)} 条"
                        f" → 过滤后 {page_passed_count} 条"
                        f"（累计通过 {len(all_reviews)} 条, 过滤 {total_rejected} 条）"
                    )
                else:
                    logger.info(
                        f"{_prefix}第 {page_num} 页完成: 解析 {len(raw_reviews)} 条"
                        f"（累计 {len(all_reviews)} 条）"
                    )

            # 更新上一个页面的 URL 作为下一页的 Referer
            referer = target_url

            # 回调进度（count/total 均为过滤后通过的数量）
            if progress_callback:
                progress_callback(
                    page_num=page_num,
                    count=page_passed_count,
                    total=len(all_reviews),
                )

            # 末页判断（基于原始解析条数，不受过滤影响）
            if not has_more:
                logger.info(f"{_prefix}已到末页（第 {page_num} 页），爬取结束")
                break

            # 正常请求间延迟（使用用户配置的间隔）
            time.sleep(delay_seconds + random.uniform(0, delay_seconds * 0.5))

        except (NetworkError, ParseError) as e:
            consecutive_errors += 1
            logger.error(f"{_prefix}第 {page_num} 页爬取出错: {e}")
            # 超过连续错误阈值时放弃
            if consecutive_errors >= 3:
                logger.error(f"{_prefix}连续错误过多，停止爬取")
                break
            _wait_with_adaptive_delay(consecutive_errors)

        except (RateLimitError, CaptchaDetectedError, CookieExpiredError) as e:
            # 这些异常需要用户介入，立即停止
            logger.error(f"{_prefix}爬取中断: {e}")
            # 将异常信息通过回调传递
            if progress_callback:
                progress_callback(
                    page_num=page_num,
                    count=0,
                    total=len(all_reviews),
                    error=str(e),
                )
            break

    session.close()
    return all_reviews, total_rejected
