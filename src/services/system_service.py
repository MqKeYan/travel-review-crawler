"""
模块名称：系统设置服务

功能说明：
    - 应用配置的读取和保存（settings.json）
    - 系统状态查询（版本、运行时间等）
    - 代理测试
    - 数据目录路径查询
"""

import json
import copy
import shutil
import time
import logging
import sys
from datetime import datetime
from typing import Any

import requests

from src import __version__
from src.utils.paths import (
    get_settings_path,
    get_data_dir_display,
    is_data_dir_writable,
    get_data_dir,
    get_cookies_dir,
)

logger = logging.getLogger("tour-crawler.system_service")

# 默认应用设置
DEFAULT_SETTINGS = {
    "window": {
        "width": 1280,
        "height": 720,
        "x": None,
        "y": None,
        "sidebar_width": 130,
    },
    "theme": "dark",
    "notifications": {
        "desktop_popup": True,
        "sound_enabled": True,
        "sound_file": "default",
        "pushplus_token": "",
    },
    "export": {
        "default_path": "",
        "default_formats": ["xlsx"],
    },
    "notify": {
        "default_desktop_popup": True,
        "default_sound": False,
        "default_pushplus_token": "",
    },
    "proxy": {
        "enabled": False,
        "http": "",
        "https": "",
    },
    "crawl": {
        "default_max_count": None,
        "default_max_pages": None,
        "default_delay_seconds": 2,
        "default_remove_images": False,
        "default_remove_emoji": False,
        "default_skip_pure_emoji": False,
        "default_ad_filter": False,
    },
}


class SystemService:
    """
    系统设置服务。

    管理全局应用配置，包括窗口布局、主题、通知、代理等。
    设置文件保存为 JSON 格式，位于运行目录的 settings.json。
    """

    def __init__(self):
        self._start_time = time.time()
        self._settings = copy.deepcopy(DEFAULT_SETTINGS)
        self._load_settings()
        # 缓存 psutil Process 对象，避免 cpu_percent 每次新建导致始终返回 0
        self._process = None
        try:
            import psutil
            self._process = psutil.Process()
            self._process.cpu_percent()  # 首次调用初始化基线
        except Exception:
            pass

    def _load_settings(self) -> None:
        """从 settings.json 加载设置"""
        path = get_settings_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 合并保存的设置到默认设置（保留默认值中的新字段）
                self._deep_merge(self._settings, saved)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"加载设置失败，使用默认设置: {e}")

    def _save_settings(self) -> None:
        """保存设置到 settings.json，清理已废弃的旧字段"""
        path = get_settings_path()
        try:
            # 清理 crawl 中不在默认模板里的废弃字段
            for section, defaults in DEFAULT_SETTINGS.items():
                if isinstance(defaults, dict) and section in self._settings:
                    clean = {}
                    for k, v in self._settings[section].items():
                        if k in defaults:
                            clean[k] = v
                    self._settings[section] = clean
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"保存设置失败: {e}")

    def _deep_merge(self, base: dict, override: dict) -> None:
        """递归合并字典（override 中的值覆盖 base）"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get_status(self) -> dict:
        """
        获取系统状态信息。

        Returns:
            包含版本、运行时间、数据目录、磁盘空间等信息的字典
        """
        elapsed = time.time() - self._start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)

        # Cookie 文件数量（递归统计平台子目录中的 json 文件）
        try:
            cookies_dir = get_cookies_dir()
            cookie_count = sum(1 for f in cookies_dir.rglob("*.json") if f.is_file())
        except Exception:
            cookie_count = 0

        # 软件实时内存占用 (MB)
        try:
            if self._process is None:
                import psutil
                self._process = psutil.Process()
                self._process.cpu_percent()
            mem_info = self._process.memory_info()
            memory_mb = int(mem_info.rss / (1024 * 1024))
        except Exception:
            memory_mb = 0

        # 软件数据目录硬盘占用 (MB)
        try:
            data_dir = get_data_dir()
            app_disk_mb = int(sum(
                f.stat().st_size for f in data_dir.rglob("*") if f.is_file()
            ) / (1024 * 1024))
        except Exception:
            app_disk_mb = 0

        # 软件实时 CPU 占用 (%)，除以核心数归一化到与任务管理器一致
        try:
            import psutil
            cpu_percent = self._process.cpu_percent() / psutil.cpu_count()
        except Exception:
            cpu_percent = 0.0

        # 数据目录所在磁盘剩余空间 (GB)
        try:
            usage = shutil.disk_usage(data_dir)
            disk_free_gb = int(usage.free / (1024 ** 3))
        except Exception:
            disk_free_gb = 0

        # 代理状态
        proxy_enabled = self._settings.get("proxy", {}).get("enabled", False)

        # 格式化启动时间
        started_at = datetime.fromtimestamp(self._start_time).strftime("%Y-%m-%d %H:%M")

        return {
            "version": __version__,
            "runtime": f"{hours}小时{minutes}分钟{seconds}秒",
            "data_dir": get_data_dir_display(),
            "data_dir_writable": is_data_dir_writable(),
            "cookie_count": cookie_count,
            "cpu_percent": round(cpu_percent, 1),
            "memory_mb": memory_mb,
            "app_disk_mb": app_disk_mb,
            "disk_free_gb": disk_free_gb,
            "proxy_enabled": proxy_enabled,
            "started_at": started_at,
        }

    def get_settings(self) -> dict:
        """获取完整设置字典"""
        return dict(self._settings)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取指定设置项的值（支持点号分隔路径）。

        Args:
            key: 设置键名，支持 "notifications.desktop_popup" 格式
            default: 未找到时的默认值

        Returns:
            设置值
        """
        parts = key.split(".")
        value = self._settings
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default
        return value

    def update_settings(self, new_settings: dict) -> None:
        """
        更新设置。

        Args:
            new_settings: 要更新的设置字典，只更新提供的字段
        """
        self._deep_merge(self._settings, new_settings)
        self._save_settings()

    def get_theme(self) -> str:
        """
        获取当前主题标识，若为 "auto" 则自动检测系统主题。

        兼容旧版 "dark_forest" → "dark" 映射。

        Returns:
            实际主题标识 ("dark" 或 "light")
        """
        theme = self._settings.get("theme", "dark")
        # 兼容旧版主题名称
        if theme == "dark_forest":
            theme = "dark"
        if theme not in ("dark", "light", "auto"):
            theme = "dark"
        if theme == "auto":
            return self.detect_system_theme()
        return theme

    def get_raw_theme(self) -> str:
        """
        获取用户设置的主题标识（不解析 auto）。

        Returns:
            原始主题标识 ("dark" / "light" / "auto")
        """
        theme = self._settings.get("theme", "dark")
        if theme == "dark_forest":
            theme = "dark"
        if theme not in ("dark", "light", "auto"):
            theme = "dark"
        return theme

    def set_theme(self, theme: str) -> None:
        """
        设置主题。

        Args:
            theme: 主题标识 ("dark" / "light" / "auto")
        """
        if theme in ("dark", "light", "auto"):
            self._settings["theme"] = theme
            self._save_settings()

    @staticmethod
    def detect_system_theme() -> str:
        """
        检测 Windows 系统主题。

        通过注册表读取 AppsUseLightTheme 键值：
        1 = 浅色主题 → "light"
        0 = 深色主题 → "dark"

        Returns:
            系统主题标识 ("dark" 或 "light")
        """
        if sys.platform != "win32":
            return "dark"
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except Exception:
            return "dark"

    def test_proxy(self, proxy_url: str) -> bool:
        """
        测试代理连通性。

        使用代理访问 http://httpbin.org/ip，
        检查返回的 IP 是否与不使用时不同。

        Args:
            proxy_url: 代理 URL（如 "http://127.0.0.1:8080"）

        Returns:
            True 表示代理可用
        """
        if not proxy_url:
            return False
        try:
            proxies = {"http": proxy_url, "https": proxy_url}
            response = requests.get(
                "http://httpbin.org/ip",
                proxies=proxies,
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
