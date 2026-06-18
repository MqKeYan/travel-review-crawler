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

from src.engine.ua_spoofer import get_random_headers, get_headers_for_api
from src.engine.cookie_manager import load_cookies_from_file
from src.sites.base import SiteAdapter, RequestType, parse_response, _get_nested_value, extract_resource_id
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


def _create_session(cookie_file: str | None = None) -> requests.Session:
    """
    创建并配置 requests.Session。

    为 Session 配置连接池、重试策略，并可选注入 Cookie。

    Args:
        cookie_file: Cookie 文件名（如 "ctrip.json"），
                     None 或空字符串表示不注入 Cookie

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
    if cookie_file:
        # 从文件名提取网站标识（如 "ctrip.json" → "ctrip"）
        site = cookie_file.replace(".json", "")
        cookies = load_cookies_from_file(site)
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

    根据适配器的 http_method 和 request_type 自动选择 GET/POST 和请求头类型。

    Args:
        session: 已配置的 requests.Session
        adapter: 网站适配器
        page_num: 当前页码（用于填充 URL 模板）
        referer: Referer 请求头（模拟来源页面）
        extra_headers: 额外的请求头（覆盖默认值）

    Returns:
        HTTP 响应对象

    Raises:
        requests.RequestException: 网络请求失败
    """
    # 根据请求类型选择不同的请求头
    if adapter.request_type == RequestType.JSON_API:
        headers = get_headers_for_api()
    else:
        headers = get_random_headers()

    if referer:
        headers["Referer"] = referer

    if extra_headers:
        headers.update(extra_headers)

    # 构建请求 URL 和参数
    url = adapter.api_endpoint or target_url or ""

    params = {}
    data = None

    # 从目标 URL 提取资源 ID（如携程的 viewid 和 resourceId）
    resource_id = extract_resource_id(target_url) if target_url else None

    # 填充分页参数模板
    if adapter.http_method.name == "GET":
        params = _fill_page_param(adapter.api_params_template, page_num, viewid=resource_id, resourceId=resource_id)
    else:
        # POST 请求时，body 模板中填充页码和资源 ID
        body = _fill_page_param(adapter.api_body_template, page_num, viewid=resource_id, resourceId=resource_id)
        if body:
            data = body

    # 发送请求
    response = session.request(
        method=adapter.http_method.name,
        url=url,
        params=params if params else None,
        json=data if data and adapter.request_type == RequestType.JSON_API else None,
        data=data if data and adapter.request_type == RequestType.HTML else None,
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )

    return response


def _fill_page_param(template: dict, page_num: int, **context) -> dict:
    """
    填充请求参数模板中的占位符。

    支持 {page} 页码和 {viewid} 等自定义占位符。

    Args:
        template: 参数模板字典，如 {"page": "{page}", "pageSize": 20}
        page_num: 实际页码
        **context: 额外替换上下文，如 viewid="521"

    Returns:
        填充后的参数字典
    """
    result = {}
    for key, value in template.items():
        if isinstance(value, str):
            if "{page}" in value:
                value = value.replace("{page}", str(page_num))
            for k, v in context.items():
                if v is not None and "{" + k + "}" in value:
                    value = value.replace("{" + k + "}", str(v))
        result[key] = value
    return result


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
            logger.info(f"第 {page_num} 页爬取被外部停止")
            return [], False

        try:
            response = _make_request(session, adapter, page_num, referer, target_url=target_url)
        except requests.RequestException as e:
            last_error = e
            if attempt < MAX_RETRY_COUNT - 1:
                # 指数退避：1s → 3s → 9s
                delay = RETRY_BACKOFF_BASE * (3 ** attempt)
                logger.warning(
                    f"第 {page_num} 页请求失败（第{attempt+1}次/共{MAX_RETRY_COUNT}次）"
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
            logger.warning(f"第 {page_num} 页返回非 200 状态码: {response.status_code}")
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
) -> list[dict]:
    """
    爬取指定网站的全部评论数据（多页自动翻页）。

    如果适配器设置了 selenium_crawler，则使用 Selenium 翻页爬取。
    否则使用常规的 requests 请求 + 翻页。

    Args:
        adapter: 网站适配器
        cookie_file: Cookie 文件名
        max_pages: 最大翻页数限制，None 表示使用适配器的默认值
        max_count: 最大条数限制，达到后停止
        progress_callback: 进度回调函数，接收 (page_num, reviews, total_count) 参数
        stop_check: 停止检测函数，返回 True 时停止爬取
        target_url: 目标页面 URL（用户输入），用作请求 Referer 和 HTML 模式的请求地址

    Returns:
        所有爬取的评论数据列表
    """
    page_limit = max_pages or adapter.max_pages_limit

    # ---- Selenium 翻页模式（需要 JS 渲染的网站） ----
    if adapter.selenium_crawler and target_url and page_limit > 1:
        logger.info(f"使用 Selenium 翻页爬取 (最多 {page_limit} 页)")
        if progress_callback:
            progress_callback(page_num=1, count=0, total=0, message="启动浏览器...")

        try:
            all_reviews = adapter.selenium_crawler(
                url=target_url,
                max_pages=page_limit,
                max_count=max_count or 0,
                timeout=600,
                stop_check=stop_check,
                progress_callback=progress_callback,
            )
        except Exception as e:
            logger.error(f"Selenium 翻页失败: {e}")
            all_reviews = []

        total = len(all_reviews)
        if progress_callback:
            progress_callback(page_num=1, count=total, total=total)
        logger.info(f"Selenium 爬取完成，共 {total} 条")
        return all_reviews

    # ---- 常规 requests 翻页模式 ----
    session = _create_session(cookie_file)
    all_reviews: list[dict] = []
    consecutive_errors = 0

    page_limit = max_pages or adapter.max_pages_limit
    referer = target_url

    for page_num in range(adapter.page_start, adapter.page_start + page_limit):
        # 检查外部停止请求
        if stop_check and stop_check():
            logger.info("爬取任务被外部停止")
            break

        # 检查是否已达到目标条数
        if max_count and len(all_reviews) >= max_count:
            break

        try:
            reviews, has_more = crawl_single_page(
                session, adapter, page_num, referer, target_url, stop_check
            )

            consecutive_errors = 0  # 成功，重置连续失败计数

            if reviews:
                all_reviews.extend(reviews)
                # 达到 max_count 时截断多余数据
                if max_count and len(all_reviews) > max_count:
                    all_reviews = all_reviews[:max_count]
                logger.info(
                    f"第 {page_num} 页完成: 解析 {len(reviews)} 条"
                    f"（累计 {len(all_reviews)} 条）"
                )

            # 更新上一个页面的 URL 作为下一页的 Referer
            # （实际项目中可在 crawl_single_page 中返回当前页 URL）
            referer = target_url

            # 回调进度
            if progress_callback:
                progress_callback(
                    page_num=page_num,
                    count=len(reviews),
                    total=len(all_reviews),
                )

            # 末页判断
            if not has_more:
                logger.info(f"已到末页（第 {page_num} 页），爬取结束")
                break

            # 正常请求间延迟（使用用户配置的间隔）
            time.sleep(delay_seconds + random.uniform(0, delay_seconds * 0.5))

        except (NetworkError, ParseError) as e:
            consecutive_errors += 1
            logger.error(f"第 {page_num} 页爬取出错: {e}")
            # 超过连续错误阈值时放弃
            if consecutive_errors >= 3:
                logger.error("连续错误过多，停止爬取")
                break
            _wait_with_adaptive_delay(consecutive_errors)

        except (RateLimitError, CaptchaDetectedError, CookieExpiredError) as e:
            # 这些异常需要用户介入，立即停止
            logger.error(f"爬取中断: {e}")
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
    return all_reviews
