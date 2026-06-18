"""
模块名称：UA 随机伪装模块

功能说明：
    - 每次爬虫请求时自动随机伪装 User-Agent
    - 支持 Edge/Chrome/Firefox 三种浏览器类型
    - fake-useragent 库 + 静态 UA 池双重保障
    - 提供完整的请求头伪装（Accept、Sec-Fetch 等）

依赖模块：
    - random (标准库)
    - fake-useragent (第三方)
"""

import random
from fake_useragent import UserAgent


# 静态 UA 池作为 fake-useragent 库的 fallback（按浏览器分类）
# 每个浏览器保留 3 个主流版本的 UA 字符串
UA_POOL = {
    "edge": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    ],
    "chrome": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    ],
    "firefox": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    ],
}

# 支持的浏览器类型列表（用于随机选择）
BROWSER_TYPES = list(UA_POOL.keys())


def get_random_ua(browser: str | None = None) -> tuple[str, str]:
    """
    获取随机的 User-Agent 字符串。

    优先使用 fake-useragent 库获取实时更新的 UA，
    失败时回退到静态 UA 池。

    Args:
        browser: 指定的浏览器类型（"edge" / "chrome" / "firefox"），
                 None 表示随机选择一种

    Returns:
        (user_agent_string, browser_type) 元组

    Example:
        >>> ua, browser = get_random_ua("chrome")
        >>> print(ua)
        Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
        >>> print(browser)
        chrome
    """
    if browser is None:
        browser = random.choice(BROWSER_TYPES)

    # 确保 browser 参数在支持的范围内
    if browser not in UA_POOL:
        browser = random.choice(BROWSER_TYPES)

    try:
        # 优先使用 fake-useragent 库（实时更新，更真实）
        ua = UserAgent(browsers=[browser])
        ua_str = ua.random
        # 验证返回的 UA 确实包含目标浏览器的标识符
        # 某些情况下 fake-useragent 可能返回错误浏览器类型的 UA
        if _ua_matches_browser(ua_str, browser):
            return ua_str, browser
    except Exception:
        pass

    # fake-useragent 不可用或返回了错误的 UA 类型，回退到静态池
    return random.choice(UA_POOL[browser]), browser


def _ua_matches_browser(ua_string: str, browser: str) -> bool:
    """
    验证 UA 字符串是否匹配指定的浏览器类型。

    通过检查 UA 中是否包含该浏览器的独有标识符来判断。

    Args:
        ua_string: User-Agent 字符串
        browser: 浏览器类型（"edge" / "chrome" / "firefox"）

    Returns:
        True 表示 UA 与浏览器类型匹配
    """
    if browser == "edge":
        return "Edg/" in ua_string
    elif browser == "chrome":
        return "Chrome/" in ua_string and "Edg/" not in ua_string
    elif browser == "firefox":
        return "Firefox/" in ua_string and "Gecko/" in ua_string
    return True


def get_random_headers(browser: str | None = None) -> dict:
    """
    获取完整的随机请求头集合。

    模拟真实浏览器发出的请求头，降低被反爬虫机制识别的风险。
    不同浏览器类型的请求头略有差异（如 Firefox 的 Accept 值不同）。

    Args:
        browser: 指定的浏览器类型，None 表示随机选择

    Returns:
        包含完整请求头的字典，可直接用于 requests.get(headers=...)

    Example:
        >>> headers = get_random_headers()
        >>> response = requests.get(url, headers=headers)
    """
    ua_string, browser_type = get_random_ua(browser)

    # 构建基础请求头
    # Sec-Fetch-* 系列头是现代浏览器自动发送的安全头，模拟它们使请求更真实
    headers = {
        "User-Agent": ua_string,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    # Firefox 的 Accept 头部有不同格式，与其他浏览器区分
    if browser_type == "firefox":
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

    return headers


def get_headers_for_api(browser: str | None = None) -> dict:
    """
    获取适用于 JSON API 请求的请求头。

    与 get_random_headers 的区别：
    - 不包含 Upgrade-Insecure-Requests
    - Accept 指定为 JSON 格式
    - 添加 Origin 和 Referer（因需要根据场景动态设置，此处不设值）

    Args:
        browser: 指定的浏览器类型

    Returns:
        JSON API 场景的请求头
    """
    ua_string, browser_type = get_random_ua(browser)

    headers = {
        "User-Agent": ua_string,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    return headers
