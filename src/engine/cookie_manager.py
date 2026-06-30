"""
模块名称：Cookie 管理模块

功能说明：
    - 通过 Selenium 驱动系统浏览器（Edge → Chrome → Firefox）打开登录页
    - 用户登录后从浏览器会话中提取 Cookie
    - Cookie 以明文 JSON 保存到运行目录 cookies/ 下
    - 从运行目录读取已保存的 Cookie

依赖模块：
    - os, subprocess, json, datetime, logging (标准库)
    - selenium (第三方)
    - src.utils.paths: get_cookies_dir()
"""

import os
import json
import datetime
import logging

from src.utils.paths import get_cookies_dir, get_cookie_platform_dir
from src.utils.exceptions import CookieExtractError

logger = logging.getLogger("tour-crawler.cookie_manager")


# ==================== Selenium 驱动浏览器提取 Cookie ====================

# 指示登录成功的 Cookie 名称关键词（任意一个出现即视为已登录）
_LOGIN_COOKIE_NAMES = {"cticket", "login_uid", "S_token", "token", "sid", "dper", "unb"}
_LOGIN_WAIT_TIMEOUT = 600  # 登录等待超时（秒）

# 按优先级排列的浏览器驱动列表
_SELENIUM_BROWSERS = [
    {
        "name": "edge",
        "driver_module": "selenium.webdriver.edge.options",
        "options_class": "Options",
        "webdriver_class": "Edge",
    },
    {
        "name": "chrome",
        "driver_module": "selenium.webdriver.chrome.options",
        "options_class": "Options",
        "webdriver_class": "Chrome",
    },
    {
        "name": "firefox",
        "driver_module": "selenium.webdriver.firefox.options",
        "options_class": "Options",
        "webdriver_class": "Firefox",
    },
]


def _create_browser_driver(browser_config: dict):
    """
    创建指定浏览器的 Selenium WebDriver 实例。

    Args:
        browser_config: 浏览器配置字典（name, options_class, webdriver_class）

    Returns:
        WebDriver 实例

    Raises:
        Exception: 驱动创建失败时抛出
    """
    import importlib

    opts_mod = importlib.import_module(browser_config["driver_module"])
    Options = getattr(opts_mod, browser_config["options_class"])

    webdriver_mod = importlib.import_module("selenium.webdriver")
    WebDriver = getattr(webdriver_mod, browser_config["webdriver_class"])

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = WebDriver(options=options)
    return driver


def open_browser_wait_for_login_auto(
    login_url: str,
    domain: str,
    status_callback=None,
    timeout: int = None,
) -> list[dict]:
    """
    一步完成：打开浏览器 → 等待用户登录（自动检测）→ 提取 Cookie → 关闭浏览器。

    检测登录的依据（任一满足即视为登录成功）：
    1. 浏览器中出现 {cticket, login_uid, S_token, token, sid} 中的任意 Cookie
    2. 浏览器 URL 离开了登录页且已出现登录态 Cookie

    Args:
        login_url: 登录页 URL
        domain: Cookie 所属域名
        status_callback: 可选状态回调函数 status(text)
        timeout: 超时秒数，默认 600 秒（10 分钟）

    Returns:
        Cookie 字典列表 [{name, value, domain, path}]，超时或失败返回空列表
    """
    import time
    global _selenium_driver
    timeout = timeout or _LOGIN_WAIT_TIMEOUT

    logger.info(f"开始获取 Cookie: domain={domain}, login_url={login_url}")

    # 启动浏览器
    _selenium_driver = None
    last_error = None
    for browser in _SELENIUM_BROWSERS:
        try:
            driver = _create_browser_driver(browser)
            driver.get(login_url)
            _selenium_driver = driver
            logger.info(f"已启动 {browser['name']} 浏览器，导航到登录页")
            if status_callback:
                status_callback(f"已打开 {browser['name']} 浏览器，请在窗口中登录...")
            break
        except Exception as e:
            logger.warning(f"{browser['name']} 浏览器启动失败: {e}")
            last_error = e
            continue

    if _selenium_driver is None:
        logger.error(f"所有浏览器启动失败: {last_error}")
        raise CookieExtractError(f"所有浏览器启动失败: {last_error}")

    # 等待用户登录（轮询检测 Cookie）
    start_time = time.time()
    login_detected = False
    login_page_base = login_url.split("?")[0].split("#")[0]

    try:
        while time.time() - start_time < timeout:
            time.sleep(1)
            try:
                current_url = _selenium_driver.current_url
                cookies = _selenium_driver.get_cookies()
                cookie_names = {c["name"] for c in cookies}

                # 检测：URL 离开登录页 且 出现登录态 Cookie（双重条件防误判）
                current_base = current_url.split("?")[0].split("#")[0]
                url_left_login = login_page_base not in current_base and current_base != login_page_base
                has_login_cookie = bool(cookie_names & _LOGIN_COOKIE_NAMES)

                if url_left_login and has_login_cookie:
                    login_detected = True
                    if status_callback:
                        status_callback("检测到登录成功，正在提取 Cookie...")
                    break

            except Exception:
                break

        if login_detected:
            selenium_cookies = _selenium_driver.get_cookies()
            result = [
                {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", domain),
                    "path": c.get("path", "/"),
                }
                for c in selenium_cookies
            ]
            logger.info(f"登录成功，从浏览器提取 {len(result)} 条 Cookie")
            if status_callback:
                status_callback(f"提取完成，共 {len(result)} 条 Cookie")
            return result
        else:
            logger.warning(f"登录等待超时 ({timeout}s)，用户未完成登录")
            if status_callback:
                status_callback("登录超时或浏览器已关闭")
            return []

    finally:
        try:
            _selenium_driver.quit()
            logger.info("浏览器已关闭")
        except Exception:
            pass
        _selenium_driver = None


# ==================== Cookie 文件存取 ====================


def save_cookies_to_file(platform: str, cookie_name: str, cookies: list[dict], browser_name: str) -> str:
    """
    将 Cookie 列表保存到运行目录下对应平台的子文件夹中。

    文件格式：JSON，包含平台名、创建时间、来源浏览器、Cookie 列表。
    存储路径：cookies/{platform}/{cookie_name}.json

    Args:
        platform: 平台标识（如 "ctrip"、"dianping"）
        cookie_name: Cookie 文件名称（用户自定义）
        cookies: Cookie 字典列表
        browser_name: 来源浏览器名称

    Returns:
        保存的文件完整路径
    """
    data = {
        "platform": platform,
        "cookie_name": cookie_name,
        "created_at": datetime.datetime.now().isoformat(),
        "source_browser": browser_name,
        "cookies": cookies,
    }

    platform_dir = get_cookie_platform_dir(platform)
    filepath = os.path.join(platform_dir, f"{cookie_name}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Cookie 已保存到文件: {platform}/{cookie_name}.json ({len(cookies)} 条, 来源={browser_name})")
    return filepath


def load_cookies_from_file(platform: str, cookie_name: str) -> list[dict] | None:
    """
    从运行目录读取已保存的 Cookie 文件。

    优先从平台子目录读取，若不存在则回退到旧版根目录格式。

    Args:
        platform: 平台标识（如 "ctrip"）
        cookie_name: Cookie 文件名称

    Returns:
        Cookie 列表，如果文件不存在则返回 None
    """
    # 优先从平台子目录读取
    filepath = os.path.join(get_cookie_platform_dir(platform), f"{cookie_name}.json")
    if not os.path.exists(filepath):
        # 回退到旧版根目录格式（向后兼容）
        legacy_path = os.path.join(get_cookies_dir(), f"{cookie_name}.json")
        if os.path.exists(legacy_path):
            logger.info(f"从旧版目录加载 Cookie: {cookie_name}.json")
            filepath = legacy_path
        else:
            logger.warning(f"Cookie 文件不存在: {platform}/{cookie_name}.json")
            return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    cookies = data.get("cookies", [])
    logger.info(f"Cookie 已加载: {platform}/{cookie_name}.json ({len(cookies)} 条)")
    return cookies


def get_cookie_file_path(platform: str, cookie_name: str) -> str:
    """
    获取指定平台和 Cookie 名称对应的文件路径（不论文件是否存在）。

    Args:
        platform: 平台标识
        cookie_name: Cookie 文件名称

    Returns:
        Cookie 文件完整路径
    """
    return os.path.join(get_cookie_platform_dir(platform), f"{cookie_name}.json")


def delete_cookie_file(platform: str, cookie_name: str) -> bool:
    """
    删除指定平台下的 Cookie 文件。

    Args:
        platform: 平台标识
        cookie_name: Cookie 文件名称

    Returns:
        True 表示删除成功，False 表示文件不存在
    """
    filepath = os.path.join(get_cookie_platform_dir(platform), f"{cookie_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info(f"Cookie 文件已删除: {platform}/{cookie_name}.json")
        return True
    # 也尝试删除旧版根目录格式
    legacy_path = os.path.join(get_cookies_dir(), f"{cookie_name}.json")
    if os.path.exists(legacy_path):
        os.remove(legacy_path)
        logger.info(f"旧版 Cookie 文件已删除: {cookie_name}.json")
        return True
    return False


def list_cookies_for_platform(platform: str) -> list[str]:
    """
    列出指定平台下所有已保存的 Cookie 文件名称（不含 .json 扩展名）。

    Args:
        platform: 平台标识

    Returns:
        Cookie 名称列表，按文件名排序
    """
    platform_dir = get_cookie_platform_dir(platform)
    if not platform_dir.exists():
        return []
    files = sorted(platform_dir.glob("*.json"))
    return [f.stem for f in files]


def get_all_platform_cookies() -> dict[str, list[str]]:
    """
    获取所有平台的 Cookie 文件列表。

    Returns:
        字典 {平台标识: [Cookie名称列表]}
    """
    result = {}
    cookies_root = get_cookies_dir()
    if not cookies_root.exists():
        return result
    for item in sorted(cookies_root.iterdir()):
        if item.is_dir():
            platform = item.name
            files = sorted(item.glob("*.json"))
            if files:
                result[platform] = [f.stem for f in files]
    return result
