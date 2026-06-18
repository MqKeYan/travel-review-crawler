"""
模块名称：Cookie 服务

功能说明：
    - 封装 Cookie 管理模块，提供给 UI 层调用
    - 通过 Selenium 驱动系统浏览器实现一键获取
"""

import logging

from src.engine.cookie_manager import (
    open_browser_wait_for_login_auto,
    save_cookies_to_file,
    load_cookies_from_file,
    get_cookie_file_path,
    delete_cookie_file,
)
from src.utils.exceptions import CookieExtractError

logger = logging.getLogger("tour-crawler.cookie_service")


class CookieService:
    """
    Cookie 获取与读取服务。

    通过 Selenium 驱动系统浏览器，一键完成：
    打开浏览器 → 等待登录 → 提取 → 保存 → 关闭浏览器。
    """

    def auto_extract_cookies(self, site: str, login_url: str, cookie_name: str,
                             status_callback=None) -> bool:
        """
        一键自动获取 Cookie。

        Args:
            site: 网站标识
            login_url: 登录页 URL
            cookie_name: 保存的文件名（不含 .json）
            status_callback: 状态回调函数 status(text)

        Returns:
            True 表示获取并保存成功
        """
        from src.sites import get_site_adapter
        adapter = get_site_adapter(site)
        if adapter is None:
            logger.error(f"不支持的网站: {site}")
            return False

        domain = adapter.domain

        try:
            cookies = open_browser_wait_for_login_auto(
                login_url, domain,
                status_callback=status_callback,
            )
            if not cookies:
                logger.warning("未获取到 Cookie（超时或取消）")
                return False

            save_cookies_to_file(cookie_name, cookies, "selenium-auto")
            logger.info(f"Cookie 自动保存成功: {cookie_name} ({len(cookies)} 条)")
            return True

        except CookieExtractError as e:
            logger.error(f"Cookie 自动获取失败: {e}")
            if status_callback:
                status_callback(f"失败: {e}")
            return False

    def load_cookies(self, site: str) -> list[dict] | None:
        """读取已保存的 Cookie 文件"""
        return load_cookies_from_file(site)

    def get_cookie_path(self, site: str) -> str:
        """获取 Cookie 文件路径"""
        return get_cookie_file_path(site)

    def has_cookie(self, site: str) -> bool:
        """检查是否存在 Cookie 文件"""
        from src.utils.paths import get_cookies_dir
        return (get_cookies_dir() / f"{site}.json").exists()

    def delete_cookie(self, site: str) -> bool:
        """删除 Cookie 文件"""
        return delete_cookie_file(site)

    def clear_all(self) -> int:
        """
        删除所有已保存的 Cookie 文件。

        Returns:
            删除的文件数量
        """
        from src.utils.paths import get_cookies_dir
        cookies_dir = get_cookies_dir()
        count = 0
        try:
            for f in cookies_dir.glob("*.json"):
                f.unlink()
                count += 1
        except OSError as e:
            logger.warning(f"删除 Cookie 文件失败: {e}")
        logger.info(f"已删除 {count} 个 Cookie 文件")
        return count
