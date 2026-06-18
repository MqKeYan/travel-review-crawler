"""
模块名称：运行目录路径工具

功能说明：
    - 检测 exe 所在目录是否可写
    - 管理运行时数据目录（cookies/、logs/、exports/、tasks/）
    - 权限不足时自动切换至 %APPDATA% 目录
    - 在开发模式下（未打包）使用项目根目录

依赖模块：
    - os, sys, pathlib (标准库)
"""

import os
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    """
    获取应用程序的基目录。

    检测策略：
    1. 如果是 PyInstaller 打包后的 exe，使用 exe 所在目录
    2. 如果是开发模式（python main.py），使用项目根目录

    Returns:
        基目录的 Path 对象
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包模式：exe 所在目录
        return Path(sys.executable).parent
    else:
        # 开发模式：项目根目录（main.py 所在目录的父级）
        # 假设 main.py 在 src/ 下，项目根在 src/..
        return Path(__file__).resolve().parent.parent.parent


# 缓存基目录、数据目录和可写状态，避免重复检测
_base_dir: Path = _get_base_dir()
_data_dir: Path | None = None
_is_writable: bool | None = None


def _check_writable(directory: Path) -> bool:
    """
    检测目录是否可写。

    尝试在目标目录创建临时文件并删除，以此判断写入权限。
    比 os.access() 更可靠，因为 Windows 权限模型较复杂。

    Args:
        directory: 要检测的目录路径

    Returns:
        True 表示可写，False 表示不可写
    """
    try:
        test_file = directory / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


def _ensure_dir(directory: Path) -> Path:
    """
    确保目录存在，不存在则创建。

    Args:
        directory: 目标目录路径

    Returns:
        目录路径（创建后已存在）

    Raises:
        PermissionError: 无法创建目录
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_data_dir() -> Path:
    """
    获取可写的运行时数据目录。

    自适应策略：
    1. 先检测 exe 所在目录是否可写
    2. 可写 → 使用 exe 所在目录
    3. 不可写（如 C:/Program Files）→ 使用 %APPDATA%/tour-crawler/

    Returns:
        可写目录路径
    """
    global _data_dir

    if _data_dir is not None:
        return _data_dir

    if _check_writable(_base_dir):
        _data_dir = _base_dir
    else:
        # 切换到 %APPDATA% 目录
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        _data_dir = appdata / "tour-crawler"
        _ensure_dir(_data_dir)

    return _data_dir


def is_data_dir_writable() -> bool:
    """
    检测数据目录是否可写（用于 UI 展示）。

    Returns:
        True 表示可写入 exe 所在目录，False 表示已切换到 %APPDATA%
    """
    global _is_writable

    if _is_writable is not None:
        return _is_writable

    _is_writable = _check_writable(_base_dir)
    return _is_writable


def get_cookies_dir() -> Path:
    """获取 Cookie 存储目录路径，不存在则自动创建"""
    path = get_data_dir() / "cookies"
    return _ensure_dir(path)


def get_logs_dir() -> Path:
    """获取日志存储目录路径，不存在则自动创建"""
    path = get_data_dir() / "logs"
    return _ensure_dir(path)


def get_exports_dir() -> Path:
    """获取导出文件存储目录路径，不存在则自动创建"""
    path = get_data_dir() / "exports"
    return _ensure_dir(path)


def get_tasks_dir() -> Path:
    """获取任务进度 JSON 存储目录路径，不存在则自动创建"""
    path = get_data_dir() / "tasks"
    return _ensure_dir(path)


def get_settings_path() -> Path:
    """获取配置文件路径（如果文件不存在不会自动创建）"""
    return get_data_dir() / "settings.json"


def get_data_dir_display() -> str:
    """
    获取用户可读的数据目录路径。
    用于设置页显示当前数据目录位置。
    """
    return str(get_data_dir())
