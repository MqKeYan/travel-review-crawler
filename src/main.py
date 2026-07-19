"""
模块名称：应用入口

功能说明：
    - PySide6 桌面应用的启动入口
    - 配置高 DPI 自适应
    - 初始化 QApplication
    - 创建和显示主窗口
    - 捕获全局异常，避免崩溃

使用方式：
    cd src && python main.py

环境要求：
    - Python 3.13+
    - PySide6 6.8+
    - 所有依赖库使用最新版本
"""

import sys
import os
import signal
import traceback

# 确保项目根目录在 Python 路径中最前面
# 这样包导入（from src.xxx import ...）才能正常工作
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src import __version__ as version

# ---- Windows 任务栏图标（必须在 QApplication 创建之前设置） ----
# 设置 AppUserModelID 后 Windows 任务栏会使用 exe 内嵌的 ico 图标，
# 而不是回退到 python.exe 的默认图标
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TourCrawler.App")
    except Exception:
        pass

# ---- 高 DPI 自适应（必须在 QApplication 创建之前配置） ----
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

# ---- Qt 渲染加速（必须在 QApplication 创建之前配置） ----
# 启用 Qt 6.4+ RHI Widget 渲染后端，将 widget 绘制从 CPU 光栅引擎
# 切换到 GPU（Direct3D 11），显著提升 QSS 样式重绘和窗口缩放性能
os.environ.setdefault("QT_WIDGETS_RHI", "1")
os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")
# 强制 Qt 使用硬件加速渲染，避免回退到软件渲染
os.environ.setdefault("QT_QUICK_BACKEND", "")       # 清空默认值，让 Qt 自动选择最优
os.environ.setdefault("QSG_RHI_PREFER_SOFTWARE_RENDERER", "0")
# 确保 Qt 平台插件路径正确（PyInstaller 打包后 qt.conf 可能缺失）
if getattr(sys, 'frozen', False):
    plugin_dir = os.path.join(sys._MEIPASS, "PySide6", "Qt6", "plugins")
    os.environ.setdefault("QT_PLUGIN_PATH", plugin_dir)


def setup_high_dpi() -> None:
    """
    配置 Qt 高 DPI 自适应策略。

    使用 PassThrough 策略允许 Qt 精确处理非整数缩放（如 125%、150%），
    配合 QT_AUTO_SCREEN_SCALE_FACTOR=1 自动适配显示器 DPI。
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def global_exception_handler(exc_type, exc_value, exc_tb) -> None:
    """
    全局异常处理函数。

    捕获未处理的异常，记录到日志并显示错误对话框。
    避免 PySide6 应用因单次未捕获异常而完全崩溃。

    Args:
        exc_type: 异常类型
        exc_value: 异常实例
        exc_tb: 堆栈回溯对象
    """
    # 忽略 KeyboardInterrupt（Ctrl+C 正常退出）
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    # 记录到日志
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        from src.utils.logger import get_logger
        logger = get_logger()
        logger.critical(f"未捕获的异常:\n{error_msg}")
    except Exception:
        # 日志模块也可能出错，回退到 stderr
        sys.stderr.write(error_msg)

    # 显示错误对话框（如果 QApplication 已创建）
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication

        app = QApplication.instance()
        if app:
            QMessageBox.critical(
                None,
                "程序异常",
                f"程序发生未预期错误，建议重启应用。\n\n错误: {exc_value}",
            )
    except Exception:
        pass


def main() -> int:
    """
    应用主函数。

    执行流程：
    1. 配置高 DPI
    2. 注册全局异常处理器
    3. 创建 QApplication
    4. 应用暗夜绿主题
    5. 创建并显示主窗口
    6. 进入 Qt 事件循环

    Returns:
        进程退出码
    """
    # ---- 屏蔽 Qt 内部已知无害警告（必须在任何 PySide6 调用前安装） ----
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType

    _SUPPRESSED_QT_PATTERNS = [
        "QFont::setPointSize: Point size <= 0",
        "OpenType support missing",
    ]

    def _qt_message_handler(msg_type, context, msg):
        if msg_type == QtMsgType.QtWarningMsg:
            for pattern in _SUPPRESSED_QT_PATTERNS:
                if pattern in msg:
                    return
        # 默认输出到 stderr（保持 Qt 原始行为）
        sys.stderr.write(f"{msg}\n")

    qInstallMessageHandler(_qt_message_handler)

    # ---- 高 DPI 配置 ----
    setup_high_dpi()

    # ---- 全局异常处理 ----
    sys.excepthook = global_exception_handler

    # ---- 创建应用 ----
    from PySide6.QtWidgets import QApplication as QA

    app = QA(sys.argv)
    app.setApplicationName("评价爬虫器")
    app.setApplicationVersion(version)
    app.setOrganizationName("TourCrawler")
    # 显式声明：最后一个窗口关闭时退出应用
    # 配合 closeEvent 中的线程清理，确保彻底退出
    app.setQuitOnLastWindowClosed(True)

    # ---- Ctrl+C 优雅退出 ----
    # Windows 上 Qt 事件循环阻塞导致 SIGINT 无法被 Python 正常处理，
    # 通过定时器定期唤醒事件循环，让信号有机会被投递
    signal.signal(signal.SIGINT, lambda signum, frame: app.quit())

    from PySide6.QtCore import QTimer
    _sig_timer = QTimer()
    _sig_timer.timeout.connect(lambda: None)  # 空回调，仅用于唤醒事件循环处理信号
    _sig_timer.start(200)

    # 禁止未聚焦的输入控件响应滚轮（防止滚动页面时误改数值）
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox

    class _WheelGuard(QObject):
        _BLOCKED = (QSpinBox, QDoubleSpinBox, QComboBox)

        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Wheel:
                if isinstance(obj, self._BLOCKED) and not obj.hasFocus():
                    return True
            return super().eventFilter(obj, event)

    app.installEventFilter(_WheelGuard(app))

    # 设置应用图标（兼容开发模式和 PyInstaller 打包）
    from PySide6.QtGui import QIcon
    from pathlib import Path
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(_current_dir)
    app.setWindowIcon(QIcon(str(base / "assets" / "app.ico")))

    # ---- 初始化日志 ----
    from src.utils.logger import get_logger
    logger = get_logger()
    logger.info(f"应用启动 (Python {sys.version})")

    # ---- 创建主窗口 ----
    from src.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    logger.info("主窗口已显示")

    # ---- 进入事件循环 ----
    exit_code = app.exec()

    logger.info(f"应用退出, 退出码: {exit_code}")

    # ---- 确保进程完全退出（PyInstaller 打包模式） ----
    # 关闭所有可能的后台资源
    try:
        import gc
        # 强制触发垃圾回收，释放未关闭的文件句柄和连接
        gc.collect()
    except Exception:
        pass

    # 对于 PyInstaller 打包的 exe，使用 os._exit 确保进程彻底退出
    # 避免因残留的 daemon 线程、pending futures 或 DLL 导致进程挂起
    if getattr(sys, 'frozen', False):
        import os as _os
        _os._exit(exit_code)

    return exit_code


if __name__ == "__main__":
    # PyInstaller 打包模式：multiprocessing.freeze_support()
    # 防止 Windows 下产生孤儿进程
    from multiprocessing import freeze_support
    freeze_support()

    sys.exit(main())
