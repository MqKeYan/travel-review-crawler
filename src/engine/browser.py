"""
浏览器驱动工具
"""

import subprocess
import importlib


def _create_service(module_path: str):
    """创建 Service 实例，通过 popen_kw 传递 CREATE_NO_WINDOW 抑制控制台黑窗"""
    mod = importlib.import_module(module_path)
    Service = getattr(mod, "Service")
    return Service(popen_kw={"creation_flags": subprocess.CREATE_NO_WINDOW})


def create_edge_driver(options=None):
    """创建 Edge WebDriver，自动隐藏控制台黑窗"""
    from selenium import webdriver

    service = _create_service("selenium.webdriver.edge.service")
    return webdriver.Edge(options=options, service=service)


def create_edge_driver_minimized(options=None):
    """
    创建正常显示但启动后最小化的 Edge WebDriver（阿里系平台使用）。

    窗口正常显示以便用户手动完成验证码，
    启动后立即最小化避免干扰用户。
    """
    from selenium import webdriver

    if options is None:
        from selenium.webdriver.edge.options import Options
        options = Options()

    # 正常窗口显示（不设置 --window-position 屏幕外隐藏）
    # 启动后由调用方通过 driver.minimize_window() 最小化
    service = _create_service("selenium.webdriver.edge.service")
    driver = webdriver.Edge(options=options, service=service)
    try:
        driver.minimize_window()
    except Exception:
        pass
    return driver


def create_driver(browser_name: str, options):
    """通用浏览器 WebDriver 创建（用于 cookie_manager 动态浏览器场景）"""
    webdriver_mod = importlib.import_module("selenium.webdriver")
    WebDriver = getattr(webdriver_mod, browser_name.capitalize())

    service = _create_service(f"selenium.webdriver.{browser_name}.service")
    return WebDriver(options=options, service=service)