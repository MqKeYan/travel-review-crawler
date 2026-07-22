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
    list_cookies_for_platform,
    get_all_platform_cookies,
)
from src.utils.paths import get_cookies_dir, get_cookie_platform_dir
from src.utils.exceptions import CookieExtractError

logger = logging.getLogger("tour-crawler.cookie_service")


class CookieService:
    """
    Cookie 获取与读取服务。

    通过 Selenium 驱动系统浏览器，一键完成：
    打开浏览器 → 等待登录 → 提取 → 保存 → 关闭浏览器。
    """

    def auto_extract_cookies(self, platform: str, login_url: str, cookie_name: str,
                             status_callback=None) -> bool:
        """
        一键自动获取 Cookie。

        Args:
            platform: 平台标识（如 "ctrip"）
            login_url: 登录页 URL
            cookie_name: 保存的文件名（不含 .json）
            status_callback: 状态回调函数 status(text)

        Returns:
            True 表示获取并保存成功
        """
        from src.sites import get_site_adapter
        adapter = get_site_adapter(platform)
        if adapter is None:
            logger.error(f"不支持的平台: {platform}")
            return False

        domain = adapter.domain
        login_cookie_names = adapter.login_cookie_names

        try:
            cookies = open_browser_wait_for_login_auto(
                login_url, domain,
                status_callback=status_callback,
                login_cookie_names=login_cookie_names,
            )
            if not cookies:
                logger.warning("未获取到 Cookie（超时或取消）")
                return False

            # 使用适配器指定的 cookie_platform（如携程系统一用 "ctrip"）
            cookie_platform = adapter.cookie_platform or platform
            save_cookies_to_file(cookie_platform, cookie_name, cookies, "selenium-auto")
            logger.info(f"Cookie 自动保存成功: {cookie_name}")
            return True

        except CookieExtractError as e:
            logger.error(f"Cookie 自动获取失败: {e}")
            if status_callback:
                status_callback(f"失败: {e}")
            return False

    def load_cookies(self, platform: str, cookie_name: str) -> list[dict] | None:
        """读取已保存的 Cookie 文件"""
        result = load_cookies_from_file(platform, cookie_name)
        if result:
            logger.info(f"Cookie 已加载: {platform}/{cookie_name} ({len(result)} 条)")
        else:
            logger.warning(f"Cookie 文件不存在或为空: {platform}/{cookie_name}")
        return result

    def get_cookie_path(self, platform: str, cookie_name: str) -> str:
        """获取 Cookie 文件路径"""
        return get_cookie_file_path(platform, cookie_name)

    def has_cookie(self, platform: str, cookie_name: str) -> bool:
        """检查指定平台的指定 Cookie 文件是否存在"""
        return (get_cookie_platform_dir(platform) / f"{cookie_name}.json").exists()

    def has_any_cookie(self, platform: str) -> bool:
        """检查指定平台是否有任何已保存的 Cookie"""
        return len(list_cookies_for_platform(platform)) > 0

    def list_platform_cookies(self, platform: str) -> list[str]:
        """列出指定平台下所有已保存的 Cookie 名称"""
        return list_cookies_for_platform(platform)

    def delete_cookie(self, platform: str, cookie_name: str) -> bool:
        """删除指定平台的 Cookie 文件"""
        result = delete_cookie_file(platform, cookie_name)
        if result:
            logger.info(f"Cookie 已删除: {platform}/{cookie_name}")
        else:
            logger.warning(f"Cookie 删除失败或不存在: {platform}/{cookie_name}")
        return result

    def clear_all(self) -> int:
        """
        删除所有已保存的 Cookie 文件（包括各平台子目录及旧版根目录文件）。

        Returns:
            删除的文件数量
        """
        logger.info("开始清空所有 Cookie 文件...")
        cookies_dir = get_cookies_dir()
        count = 0
        try:
            # 删除各平台子目录内的文件
            for item in cookies_dir.iterdir():
                if item.is_dir():
                    for f in item.glob("*.json"):
                        f.unlink()
                        count += 1
            # 删除旧版根目录下的 .json 文件
            for f in cookies_dir.glob("*.json"):
                f.unlink()
                count += 1
        except OSError as e:
            logger.warning(f"删除 Cookie 文件失败: {e}")
        logger.info(f"已删除 {count} 个 Cookie 文件")
        return count
