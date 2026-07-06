"""
浏览器驱动工具
功能：统一创建 WebDriver，自动隐藏控制台黑窗（CREATE_NO_WINDOW）
"""

import importlib

# Windows 进程标志：不创建控制台窗口
_CREATE_NO_WINDOW = 0x08000000


def _hide_console(service):
    """设置 Service 的 Windows 创建标志，抑制控制台黑窗"""
    service.creation_flags = _CREATE_NO_WINDOW
    return service


def create_edge_driver(options=None):
    """创建 Edge WebDriver，自动隐藏控制台黑窗"""
    from selenium import webdriver

    mod = importlib.import_module("selenium.webdriver.edge.service")
    Service = getattr(mod, "Service")
    service = _hide_console(Service())
    return webdriver.Edge(options=options, service=service)


def create_driver(browser_name: str, options):
    """通用浏览器 WebDriver 创建（用于 cookie_manager 动态浏览器场景）"""
    webdriver_mod = importlib.import_module("selenium.webdriver")
    WebDriver = getattr(webdriver_mod, browser_name.capitalize())

    svc_mod = importlib.import_module(f"selenium.webdriver.{browser_name}.service")
    Service = getattr(svc_mod, "Service")
    service = _hide_console(Service())
    return WebDriver(options=options, service=service)
