"""
模块名称：暗夜绿三栏主窗口

功能说明：
    - 应用的主窗口，三栏分页布局（QSplitter）
    - 侧边栏导航 + QStackedWidget 页面切换
    - 连接各页面 Signal 到服务层
    - 管理系统托盘和通知

布局结构：
    ┌──────────┬──────────────────┬──────────────────────────────┐
    │  侧边栏   │    列表栏         │        内容区                  │
    │  (60px)  │    (280px)       │        (自适应)                │
    │          │                  │                              │
    │  首页    │  (各页面自定)     │  QStackedWidget 页面容器       │
    │  任务    │                  │  首页/任务/数据/设置          │
    │  数据    │                  │                              │
    │  设置    │                  │                              │
    └──────────┴──────────────────┴──────────────────────────────┘
"""

import sys
import time
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStackedWidget, QSystemTrayIcon, QMenu,
    QApplication, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt, QTimer, QUrl, QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QSoundEffect

from src.ui.theme.dark_forest_theme import get_dark_forest_stylesheet, get_light_stylesheet, THEME_STYLESHEETS
from src.ui.components.sidebar import Sidebar
from src.ui.pages.home_page import HomePage
from src.ui.pages.task_page import TaskPage
from src.ui.pages.create_task_page import CreateTaskPage
from src.ui.pages.data_page import DataPage
from src.ui.pages.settings_page import SettingsPage
from src.ui.pages.log_page import LogPage
from src.ui.components.cookie_dialog import CookieDialog
from src.services.cookie_service import CookieService
from src.services.task_service import TaskService
from src.services.data_service import DataService
from src.services.export_service import ExportService
from src.services.site_service import SiteService
from src.services.system_service import SystemService
from src.services.stats_service import StatsService
from src.services.log_service import LogService
from src.engine.notifier import Notifier
from src.utils.logger import shutdown_logger
from src.utils.paths import get_data_dir
from src.models.task import ExportConfig, TaskStatus

# 导出格式中文名映射
_FORMAT_NAMES = {
    "xlsx": "Excel",
    "csv": "CSV",
    "txt": "文本",
    "docx": "Word",
}

logger = logging.getLogger("tour-crawler.main_window")


class _CookieWorker(QObject):
    """后台 Cookie 获取 worker，通过信号安全通知主线程"""
    status = Signal(str)
    finished = Signal(bool, str)


class MainWindow(QMainWindow):
    """
    暗夜绿三栏主窗口。

    应用的顶层窗口，管理侧边栏导航、页面切换、系统托盘和通知。
    通过依赖注入的方式持有所有服务实例。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("评价爬虫器")
        self.setMinimumSize(1300, 720)

        # ---- 初始化服务 ----
        self._site_service = SiteService()
        self._cookie_service = CookieService()
        self._task_service = TaskService()
        self._data_service = DataService()
        self._export_service = ExportService()
        self._system_service = SystemService()
        self._stats_service = StatsService()
        self._notifier = Notifier()

        # ---- 构建 UI ----
        self._setup_ui()
        self._setup_tray()
        self._setup_notifications()
        resolved_theme = self._apply_theme()
        self._log_page.set_theme(resolved_theme)
        self._connect_signals()

        # ---- 系统信息定时刷新 ----
        self._sysinfo_timer = QTimer(self)
        self._sysinfo_timer.timeout.connect(self._refresh_home_system_info)
        self._sysinfo_timer.start(1000)  # 每秒刷新，运行时间实时显示
        self._refresh_home_system_info()  # 立即填充初始值

        # ---- 窗口恢复 ----
        self._restore_window_state()

        logger.info("主窗口初始化完成")

    def _setup_ui(self) -> None:
        """初始化三栏布局主窗口"""
        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局：水平三栏
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 获取屏幕分辨率，设置初始窗口大小
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            default_width = int(screen_rect.width() * 0.80)
            default_height = int(screen_rect.height() * 0.85)
            self.resize(default_width, default_height)
        else:
            self.resize(1300, 800)

        # ===== 第一栏：侧边栏 =====
        self._sidebar = Sidebar()
        self._sidebar.setFixedWidth(145)
        self._sidebar.setMinimumWidth(130)

        # ===== 第二栏：内容区（QStackedWidget） =====
        self._stack = QStackedWidget()

        # 创建各页面（给每个页面设最小宽度防止压缩）
        self._home_page = HomePage()
        self._home_page.setMinimumWidth(600)
        self._task_page = TaskPage()
        self._task_page.setMinimumWidth(600)
        self._create_task_page = CreateTaskPage(self._site_service.get_preset_sites())
        self._create_task_page.setMinimumWidth(600)
        self._data_page = DataPage()
        self._data_page.setMinimumWidth(600)
        self._settings_page = SettingsPage()
        self._settings_page.setMinimumWidth(600)
        self._log_page = LogPage()
        self._log_page.setMinimumWidth(600)

        # 添加到栈（索引顺序对应侧边栏按钮：0=首页,1=任务,2=数据,3=设置,4=记录）
        self._stack.addWidget(self._home_page)       # 0
        self._stack.addWidget(self._task_page)       # 1
        self._stack.addWidget(self._data_page)       # 2
        self._stack.addWidget(self._settings_page)   # 3
        self._stack.addWidget(self._log_page)        # 4

        # 组装主布局：侧边栏固定宽度 + 内容区弹性填满
        main_layout.addWidget(self._sidebar)
        main_layout.addWidget(self._stack, 1)

        central.setLayout(main_layout)

        # 默认显示首页
        self._stack.setCurrentIndex(0)

    def _setup_tray(self) -> None:
        """设置系统托盘图标"""
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setToolTip("评价爬虫器")

        # 加载托盘图标（兼容开发模式和 PyInstaller 打包）
        from PySide6.QtGui import QIcon
        from pathlib import Path
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).resolve().parent.parent  # src/
        self._tray_icon.setIcon(QIcon(str(base / "assets" / "app.ico")))

        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show_and_activate)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.show()

        # 托盘点击恢复窗口
        self._tray_icon.activated.connect(
            lambda reason: self.show_and_activate() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )

    def _setup_notifications(self) -> None:
        """设置通知服务"""
        self._notifier.set_tray_icon(self._tray_icon)

        # 创建自定义音效文件夹，用户可放入 .wav/.mp3/.ogg 文件
        try:
            sounds_dir = get_data_dir() / "sounds"
            sounds_dir.mkdir(parents=True, exist_ok=True)

            # 扫描音效文件（主流音频格式）
            audio_ext = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"}
            audio_files = [f for f in sounds_dir.iterdir() if f.suffix.lower() in audio_ext]

            if audio_files:
                # 使用第一个找到的音效文件
                self._sound_effect = QSoundEffect()
                self._sound_effect.setSource(QUrl.fromLocalFile(str(audio_files[0])))
                self._sound_effect.setVolume(0.5)
                self._notifier.set_sound_effect(self._sound_effect)
        except Exception:
            pass

    def _apply_theme(self, theme: str | None = None) -> str:
        """
        应用 QSS 主题 + 窗口标题栏颜色。

        Args:
            theme: 主题标识 ("dark" / "light" / "auto")，None 时从设置读取。
                   自动解析 "auto" 为系统实际主题。

        Returns:
            实际应用的主题标识 ("dark" / "light")
        """
        if theme is None:
            theme = self._system_service.get_theme()
        elif theme == "auto":
            theme = self._system_service.detect_system_theme()

        getter = THEME_STYLESHEETS.get(theme, get_dark_forest_stylesheet)
        stylesheet = getter()

        # 禁用窗口更新，避免逐个 widget 重绘（消除切换闪烁）
        self.setUpdatesEnabled(False)
        self.setStyleSheet(stylesheet)
        self.setUpdatesEnabled(True)

        # 适配 Windows 标题栏颜色
        self._apply_titlebar_theme(theme)

        logger.info(f"主题已切换为: {theme}")
        return theme

    def _apply_titlebar_theme(self, theme: str) -> None:
        """
        设置 Windows 标题栏颜色以匹配软件主题色系。

        暗夜绿 → 深色标题栏 (#0f120f)
        晨曦绿 → 浅色标题栏 (#f5f7f5)

        通过 Windows DWM API 实现：
        - Windows 10: DWMWA_USE_IMMERSIVE_DARK_MODE (暗/亮模式)
        - Windows 11: DWMWA_CAPTION_COLOR (自定义标题栏颜色)
        """
        import ctypes
        from ctypes import wintypes

        try:
            hwnd = int(self.winId())
        except Exception:
            return

        # --- Windows 11: 自定义标题栏背景色 ---
        # DWMWA_CAPTION_COLOR = 35
        try:
            color_value = 0x000F120F if theme == "dark" else 0x00F5F7F5  # BGR
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_uint(35),
                ctypes.byref(ctypes.c_uint(color_value)),
                ctypes.sizeof(ctypes.c_uint),
            )
        except Exception:
            pass

        # --- Windows 10: 沉浸式暗色/亮色标题栏 ---
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        try:
            dark_mode = ctypes.c_int(1 if theme == "dark" else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_uint(20),
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode),
            )
        except Exception:
            pass

    def _connect_signals(self) -> None:
        """连接各组件之间的 Signal 和 Slot"""

        # ---- 侧边栏导航 ----
        self._sidebar.page_changed.connect(self._on_page_changed)

        # ---- 首页导航 ----
        self._home_page.navigate.connect(self._sidebar.set_active)

        # ---- 任务页面 ----
        self._task_page.create_task_requested.connect(self._on_create_task_requested)
        self._task_page.task_start_requested.connect(self._on_task_start)
        self._task_page.task_pause_requested.connect(self._on_task_pause)
        self._task_page.task_stop_requested.connect(self._on_task_stop)
        self._task_page.task_delete_requested.connect(self._on_task_delete)

        # ---- 新建任务页面 ----
        self._create_task_page.task_created.connect(self._on_task_created)
        self._create_task_page.get_cookie.connect(self._on_get_cookie)
        self._create_task_page.cancel.connect(self._on_create_task_cancel)

        # ---- 数据页面 ----
        self._data_page.export_requested.connect(
            lambda task, formats, fields, only_sel: self._on_export_requested(task, formats, fields, only_sel)
        )
        self._data_page.task_selected.connect(self._on_data_task_selected)

        # ---- 设置页面 ----
        self._settings_page.settings_updated.connect(self._on_settings_updated)
        self._settings_page.proxy_test_requested.connect(self._on_test_proxy)
        self._settings_page.theme_changed.connect(self._on_theme_changed)
        self._settings_page.clear_data_requested.connect(self._on_clear_data)
        self._settings_page.reset_settings_requested.connect(self._on_reset_settings)
        self._settings_page.reinitialize_requested.connect(self._on_reinitialize)

    # ==================== 页面导航 ====================

    def _on_page_changed(self, page_index: int) -> None:
        """侧边栏页面切换"""
        # 如果新建任务页面在 stack 中（被插入过），先移除
        if self._stack.indexOf(self._create_task_page) != -1:
            self._stack.removeWidget(self._create_task_page)

        # 跳转到目标页面（移除后索引恢复为 0=首页 1=任务 2=数据 3=设置 4=记录）
        if page_index < self._stack.count():
            # 进入任务页时清空右侧详情面板，确保每次点击"任务管理"都显示空白
            if page_index == 1:
                self._task_page.clear_detail()
            self._stack.setCurrentIndex(page_index)

            # 切换到任务页时刷新列表
            if page_index == 1:
                self._refresh_task_list()
            # 切换到数据页时刷新列表和数据
            elif page_index == 2:
                self._refresh_data_page()

    def show_and_activate(self) -> None:
        """显示并激活窗口（从托盘恢复）"""
        self.show()
        self.activateWindow()
        self.raise_()

    # ==================== 任务相关 ====================

    def _on_create_task_requested(self) -> None:
        """
        切换到新建任务页面。

        将 CreateTaskPage 插入到 Stack 中（临时页面），
        创建完成或取消后移除。
        """
        # 传入已有任务名称用于查重
        existing = list(self._task_service._tasks.keys())
        self._create_task_page.set_existing_tasks(existing)
        # 传入参数默认值（直接从磁盘读取，确保与设置页同步）
        defaults = self._system_service.get_setting("crawl", {})
        self._create_task_page.set_defaults(dict(defaults))
        # 重置表单为默认状态
        self._create_task_page.reset_form()
        # 在索引 1（任务页）之后插入新建页面
        self._stack.insertWidget(2, self._create_task_page)
        self._stack.setCurrentIndex(2)
        self._sidebar.set_active(1)

    def _on_task_created(self, config) -> None:
        """任务创建成功"""
        task = self._task_service.create_task(config)

        # 移除新建页面，回到任务列表（右侧详情面板保持空白）
        self._stack.removeWidget(self._create_task_page)
        self._task_page.clear_detail()
        self._refresh_task_list()
        self._stack.setCurrentIndex(1)

        # 刷新任务列表
        self._refresh_task_list()

        logger.info(f"任务创建成功: {task.task_name}")

    def _on_create_task_cancel(self) -> None:
        """取消创建任务"""
        self._stack.removeWidget(self._create_task_page)
        self._stack.setCurrentIndex(0)
        self._sidebar.set_active(0)

    def _on_task_start(self, task_name: str) -> None:
        """启动任务"""
        worker = self._task_service.start_task(task_name)
        if worker:
            # 必须在 worker.start() 之前连接所有 Signal
            worker.progress.connect(
                lambda data, tn=task_name: self._on_progress(tn, data)
            )
            worker.complete.connect(
                lambda result, tn=task_name: self._on_task_complete(tn, result)
            )
            worker.error.connect(
                lambda msg, tn=task_name: self._on_task_error(tn, msg)
            )
            worker.start()  # 连接完信号后再启动线程
            self._refresh_task_list()

    def _on_task_pause(self, task_name: str) -> None:
        """暂停任务"""
        self._task_service.pause_task(task_name)
        self._refresh_task_list()

    def _on_task_stop(self, task_name: str) -> None:
        """停止任务 → 提前完成（收集已爬取的数据）"""
        worker = self._task_service.get_worker(task_name)
        reviews = worker.collected_reviews if worker else []

        self._task_service.stop_task(task_name, complete_early=True)

        # 保存已收集的数据
        if reviews:
            from src.filters import build_filter_chain
            filter_chain = build_filter_chain(self._task_service.get_task(task_name).config.filter_config)
            passed, _ = filter_chain.apply(reviews)
            self._data_service.add_reviews(task_name, passed)

        self._refresh_task_list()

    def _on_task_delete(self, task_name: str) -> None:
        """删除任务"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除任务「{task_name}」及其数据吗？")
        msg_box.setIcon(QMessageBox.Icon.Question)
        yes_btn = msg_box.addButton("确定删除", QMessageBox.ButtonRole.YesRole)
        msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
        msg_box.exec()
        if msg_box.clickedButton() == yes_btn:
            self._task_service.delete_task(task_name)
            self._task_page.clear_detail()
            self._refresh_task_list()

    def _on_progress(self, task_name: str, progress_data: dict) -> None:
        """爬取进度更新，同步到 TaskService、保存到磁盘、更新 UI"""
        task = self._task_service.get_task(task_name)
        if task:
            task.update_progress_from_dict(progress_data)
            # 进度变更时保存到磁盘
            self._task_service._save_to_disk()
            # 实时更新详情页进度条
            self._task_page.update_detail_progress(progress_data)
            # 实时刷新任务卡片状态和进度
            self._task_page.refresh_task_card(task_name)
        # 同步首页统计
        self._refresh_home_stats()

    def _on_task_complete(self, task_name: str, result: dict) -> None:
        """任务完成处理"""
        count = result.get("count", 0)
        reviews = result.get("reviews", [])
        elapsed = result.get("elapsed", "")

        # 更新任务状态（已被停止则忽略）
        task = self._task_service.get_task(task_name)
        if task:
            if task.status in (TaskStatus.CANCELLED, TaskStatus.PAUSED):
                # 用户已手动停止或暂停，收集已爬数据但不改状态
                if reviews:
                    self._data_service.add_reviews(task_name, reviews)
                logger.info(f"任务 [{task_name}] 线程已退出（状态={task.status.value}），收集 {count} 条数据")
                self._refresh_task_list()
                return
            task.status = TaskStatus.COMPLETED
            task.total_reviews = count
            task.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self._task_service._save_to_disk()

            # 使用任务的独立通知设置（弹窗 + PushPlus）
            notify_config = task.config.notify_config
            self._notifier.settings.desktop_popup = (
                notify_config.on_complete.desktop_popup if notify_config else False
            )
            self._notifier.settings.sound_enabled = (
                notify_config.on_complete.sound if notify_config else False
            )
            self._notifier.settings.pushplus_token = (
                notify_config.on_complete.pushplus_token if notify_config else ""
            )

        # 任务未被删除才执行收尾操作
        if task:
            # 保存数据到 DataService
            self._data_service.add_reviews(task_name, reviews)

            # 刷新详情页进度条为完成状态
            if self._task_page._selected_task_name == task_name:
                self._task_page._detail_progress.set_complete(count)

            # 通知
            self._notifier.notify_complete(task_name, count, elapsed)

            # 记录统计
            self._stats_service.record_task_completed(count, task.site)

        # 清理 worker（无论任务是否存在都要清理）
        with self._task_service._lock:
            self._task_service._workers.pop(task_name, None)

        # 刷新任务列表
        self._refresh_task_list()

        logger.info(f"任务 [{task_name}] 完成，共 {count} 条，耗时 {elapsed}")

    def _on_task_error(self, task_name: str, error_info: str) -> None:
        """任务出错处理"""
        task = self._task_service.get_task(task_name)
        # 已被用户手动停止，忽略后续错误
        if task and task.status == TaskStatus.CANCELLED:
            with self._task_service._lock:
                self._task_service._workers.pop(task_name, None)
            self._refresh_task_list()
            return
        if task:
            task.status = TaskStatus.ERROR
            task.completed_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self._task_service._save_to_disk()

            # 使用任务的独立通知设置
            notify_config = task.config.notify_config
            self._notifier.settings.desktop_popup = (
                notify_config.on_error.desktop_popup if notify_config else False
            )
            self._notifier.settings.sound_enabled = (
                notify_config.on_error.sound if notify_config else False
            )
            self._notifier.settings.pushplus_token = (
                notify_config.on_error.pushplus_token if notify_config else ""
            )

        self._notifier.notify_error("爬取任务", error_info)

        # 记录统计
        self._stats_service.record_task_error()

        # 清理 worker
        with self._task_service._lock:
            self._task_service._workers.pop(task_name, None)

        self._refresh_task_list()

    def _refresh_home_system_info(self) -> None:
        """每秒刷新首页系统信息（运行时间等动态数据）"""
        status = self._system_service.get_status()
        # 合并累计统计数据
        cumulative = self._stats_service.get_stats()
        status["cumulative_tasks"] = cumulative.get("total_tasks_completed", 0)
        status["cumulative_reviews"] = cumulative.get("total_reviews_crawled", 0)
        self._home_page.update_system_info(status)

    def _refresh_home_stats(self) -> None:
        """刷新首页看板数据（任务统计 + 数据汇总 + 图表 + 最近任务）"""
        tasks = list(self._task_service._tasks.values())

        total = len(tasks)
        pending = sum(1 for t in tasks if t.status.value == "pending")
        running = sum(1 for t in tasks if t.status.value == "running")
        completed = sum(1 for t in tasks if t.status.value == "completed")
        error = sum(1 for t in tasks if t.status.value == "error")

        # 数据汇总（内存 DataService + 磁盘任务 total_reviews 合并）
        memory_tasks = set(self._data_service.get_all_tasks_with_data())
        total_reviews = 0
        used_sites = set()
        bar_names = []
        bar_counts = []

        # 先从任务对象获取持久化数据（重启后内存数据丢失时仍有任务级计数）
        task_reviews = []
        for t in tasks:
            if t.site:
                used_sites.add(t.site)
            count = t.total_reviews
            # 内存中有该任务的数据时优先使用实时计数
            if t.task_name in memory_tasks:
                mem_stats = self._data_service.get_stats(t.task_name)
                count = max(count, mem_stats.total)
            total_reviews += count
            short_name = t.task_name if len(t.task_name) <= 10 else t.task_name[:9] + "…"
            task_reviews.append((short_name, count))

        task_reviews.sort(key=lambda x: x[1], reverse=True)
        for n, c in task_reviews[:8]:
            bar_names.append(n)
            bar_counts.append(c)

        # 完成率
        completed_tasks = completed + error
        completion_rate = round(completed / completed_tasks * 100) if completed_tasks > 0 else 0

        # 最近任务卡片列表（按创建时间倒序取前10）
        sorted_tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:10]
        from src.ui.pages.task_page import STATUS_CN
        recent_cards = []
        for t in sorted_tasks:
            recent_cards.append({
                "name": t.task_name,
                "site": t.site_display_name or t.site,
                "reviews": t.total_reviews,
                "created_at": t.created_at,
                "status": STATUS_CN.get(t.status, "未知"),
            })

        stats = {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "error": error,
            "total_reviews": total_reviews,
            "unique_reviews": total_reviews,
            "used_sites": len(used_sites),
            "completion_rate": completion_rate,
            "recent_tasks": recent_cards,
        }
        self._home_page.update_stats(stats)

    def _refresh_task_list(self) -> None:
        """刷新任务列表显示"""
        result = self._task_service.get_tasks(page=1, size=100)
        tasks_data = result.get("items", [])
        # 转化为 Task 对象列表
        tasks = []
        for td in tasks_data:
            task = self._task_service.get_task(td["task_name"])
            if task:
                tasks.append(task)

        self._task_page.set_tasks(tasks)
        self._refresh_home_stats()

    # ==================== Cookie ====================

    def _on_get_cookie(self, site: str) -> None:
        """获取 Cookie 按钮处理（在后台线程自动完成）"""
        site_info = self._site_service.get_site(site)
        if not site_info:
            return

        display_name = site_info.get("display_name", site_info["name"])
        dialog = CookieDialog(site, display_name, self)

        # 连接信号：用户点击开始 → 启动后台线程
        dialog.cookie_started.connect(
            lambda cookie_name: self._on_cookie_start(site, site_info["login_url"], cookie_name, dialog)
        )

        dialog.show()

    def _on_cookie_start(self, site: str, login_url: str, cookie_name: str, dialog) -> None:
        """在后台线程执行 Cookie 自动获取（通过信号安全通知主线程）"""
        import threading

        self._cookie_worker = worker = _CookieWorker()

        # 信号跨线程自动排队到主线程事件循环
        worker.status.connect(
            lambda text: dialog.set_status(text, "失败" not in text)
        )
        worker.finished.connect(
            lambda success, name: self._on_cookie_finished(success, name, dialog)
        )

        def _run():
            success = self._cookie_service.auto_extract_cookies(
                site, login_url, cookie_name,
                status_callback=worker.status.emit,
            )
            worker.finished.emit(success, cookie_name)

        dialog.set_status("正在打开浏览器...")
        threading.Thread(target=_run, daemon=True).start()

    def _on_cookie_finished(self, success: bool, cookie_name: str, dialog) -> None:
        """Cookie 获取完成（在主线程执行）"""
        if success:
            dialog.set_status(f"Cookie [{cookie_name}] 保存成功", success=True)
            self._create_task_page.set_cookie_status(True)
            dialog.auto_close()
        else:
            dialog.set_status("Cookie 获取失败，请重试", success=False)

    # ==================== 数据导出 ====================

    def _refresh_data_page(self) -> None:
        """刷新数据页面的任务列表，并自动加载第一个任务的数据到表格"""
        task_names = self._data_service.get_all_tasks_with_data()
        tasks_info = []
        for name in task_names:
            stats = self._data_service.get_stats(name)
            tasks_info.append({"name": name, "count": stats.total})

        self._data_page.update_task_list(tasks_info)

        # 自动加载第一个有数据的任务到表格
        if task_names:
            first_task = task_names[0]
            page_result = self._data_service.get_reviews(first_task, page=1, size=500)
            stats = self._data_service.get_stats(first_task)
            self._data_page.set_reviews(first_task, page_result.items, stats)

    def _on_data_task_selected(self, task_name: str) -> None:
        """数据页面任务选择变化，加载对应数据到表格"""
        page_result = self._data_service.get_reviews(task_name, page=1, size=500)
        stats = self._data_service.get_stats(task_name)
        self._data_page.set_reviews(task_name, page_result.items, stats)

    def _on_export_requested(
        self, task_name: str, formats: list[str],
        fields: list[str] | None = None, only_selected: bool = False,
    ) -> None:
        """导出请求处理——弹出 Windows 原生保存对话框"""
        page_result = self._data_service.get_reviews(task_name, page=1, size=10000)
        reviews = page_result.items

        if not reviews:
            QMessageBox.information(self, "提示", "没有数据可以导出")
            return

        # 仅导出表格中选中的行
        if only_selected:
            selected_rows = self._data_page._data_table.get_selected_rows()
            reviews = selected_rows if selected_rows else reviews

        # 构建文件类型过滤器
        ext_map = {"xlsx": "Excel (*.xlsx)", "csv": "CSV (*.csv)",
                    "txt": "TXT (*.txt)", "docx": "Word (*.docx)"}
        fmt_filter = ";;".join(ext_map[f] for f in formats if f in ext_map)
        default_ext = f".{formats[0]}" if formats else ".xlsx"

        # 弹出 Windows 原生保存对话框（默认定位到导出目录）
        import time
        from src.utils.paths import get_exports_dir
        exports_dir = str(get_exports_dir())
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_name = f"{exports_dir}/评论数据_{task_name}_{timestamp}"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出评论数据", default_name, fmt_filter,
        )

        if not save_path:
            return  # 用户取消

        config = ExportConfig(formats=formats, fields=fields or [], save_path=save_path)

        worker = self._export_service.export_async(reviews, config)
        if worker:
            def _on_export_done(r):
                self._data_service.mark_exported(task_name)
                QMessageBox.information(
                    self, "导出完成",
                    f"导出完成！\n共 {r.get('total_count', 0)} 条\n"
                    + "\n".join(
                        f"- {_FORMAT_NAMES.get(f['format'], f['format'].upper())}: {f['path']}"
                        for f in r.get("results", [])
                    )
                )
            worker.complete.connect(_on_export_done)
            worker.error.connect(lambda msg: QMessageBox.warning(self, "导出错误", msg))

    # ==================== 设置 ====================

    def _on_theme_changed(self, theme: str) -> None:
        """实时主题切换（从设置页面下拉框触发）"""
        resolved = self._apply_theme(theme)
        # 更新日志页面的颜色主题（须用解析后的实际主题，非 "auto"）
        self._log_page.set_theme(resolved)
        # 立即持久化主题偏好（包括 "auto"）
        self._system_service.set_theme(theme)

    def _on_settings_updated(self, settings: dict) -> None:
        """设置更新处理（自动静默保存）"""
        self._system_service.update_settings(settings)

    def _on_test_proxy(self, proxy_url: str) -> None:
        """测试代理连通性"""
        success = self._system_service.test_proxy(proxy_url)
        self._settings_page.set_proxy_test_result(success)

    def _on_clear_data(self) -> None:
        """清空累计统计数据"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认清空数据")
        msg_box.setText(
            "确定要清空累计统计数据吗？\n\n"
            "• 累计完成任务数、评论数、运行时长将被清零\n"
            "• 爬虫评论数据在关闭软件时自动清理，不受影响\n"
            "• 导出过的文件不会被删除\n"
            "• Cookie 和设置不会被影响\n\n"
            "此操作不可恢复！"
        )
        msg_box.setIcon(QMessageBox.Icon.Warning)
        yes_btn = msg_box.addButton("确定清空", QMessageBox.ButtonRole.YesRole)
        msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
        msg_box.exec()
        if msg_box.clickedButton() != yes_btn:
            return

        # 重置累计统计数据
        self._stats_service.reset()
        # 刷新首页系统信息
        self._refresh_home_system_info()
        QMessageBox.information(self, "提示", "累计统计数据已清空")

    def _on_reset_settings(self) -> None:
        """还原所有设置为默认值"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认还原设置")
        msg_box.setText(
            "确定要将所有设置恢复为默认值吗？\n\n"
            "• 代理、导出、通知等设置将重置\n"
            "• 窗口布局将恢复默认\n"
            "• Cookie 和数据不会被影响\n\n"
            "此操作不可恢复！"
        )
        msg_box.setIcon(QMessageBox.Icon.Warning)
        yes_btn = msg_box.addButton("确定还原", QMessageBox.ButtonRole.YesRole)
        msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
        msg_box.exec()
        if msg_box.clickedButton() != yes_btn:
            return

        from src.services.system_service import DEFAULT_SETTINGS
        self._system_service.update_settings(DEFAULT_SETTINGS)
        self._refresh_settings_page()
        QMessageBox.information(self, "提示", "设置已还原为默认值，部分更改需重启生效")

    def _on_reinitialize(self) -> None:
        """重新初始化（清空全部数据 + 还原设置 + 删除 Cookie）"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("⚠ 确认重新初始化")
        msg_box.setText(
            "确定要重新初始化软件吗？\n\n"
            "以下内容将被删除/重置：\n"
            "• 累计统计数据（任务数、评论数、运行时长）\n"
            "• 所有任务记录\n"
            "• 所有 Cookie 登录信息\n"
            "• 所有设置（恢复默认）\n\n"
            "不受影响的内容：\n"
            "• 已导出的文件\n\n"
            "此操作相当于首次使用软件，不可恢复！"
        )
        msg_box.setIcon(QMessageBox.Icon.Critical)
        yes_btn = msg_box.addButton("确定重新初始化", QMessageBox.ButtonRole.YesRole)
        msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
        msg_box.exec()
        if msg_box.clickedButton() != yes_btn:
            return

        # 清空任务记录
        self._task_service._tasks.clear()
        self._task_service._save_to_disk()
        # 重置统计
        self._stats_service.reset()
        # 删除所有 Cookie
        self._cookie_service.clear_all()
        # 重置设置
        from src.services.system_service import DEFAULT_SETTINGS
        self._system_service.update_settings(DEFAULT_SETTINGS)

        self._refresh_task_list()
        self._refresh_data_page()
        self._refresh_settings_page()
        self._refresh_home_system_info()
        QMessageBox.information(self, "提示", "软件已重新初始化，即将退出")
        self.close()
        QApplication.quit()

    def _refresh_settings_page(self) -> None:
        """刷新设置页面"""
        settings = self._system_service.get_settings()
        self._settings_page.load_settings(settings)

    # ==================== 窗口状态 ====================

    def moveEvent(self, event) -> None:
        """
        窗口移动事件。

        阻止窗口上边界超出屏幕顶部，避免标题栏/拖拽区域消失在屏幕外无法操作。
        """
        super().moveEvent(event)
        if self.windowState() & Qt.WindowState.WindowMaximized:
            return

        screen = QApplication.primaryScreen()
        if not screen:
            return
        screen_rect = screen.availableGeometry()

        # 禁止窗口顶部超出屏幕（留 10px 余量避免卡死）
        if self.y() < screen_rect.y():
            self.move(self.x(), screen_rect.y())
        # 如果顶部超出但底部还在屏幕外，只限制顶部（用户自己调整）
        # 如果整个窗口都在屏幕外，移回可见区域
        if self.x() + self.width() < screen_rect.x() + 100:
            self.move(screen_rect.x() + 50, self.y())

    def _restore_window_state(self) -> None:
        """恢复窗口状态（尺寸、位置、分栏比例）"""
        settings = self._system_service.get_settings()
        window_settings = settings.get("window", {})

        # 恢复窗口尺寸
        width = window_settings.get("width", 1280)
        height = window_settings.get("height", 720)
        x = window_settings.get("x")
        y = window_settings.get("y")

        if x is not None and y is not None:
            # 确保恢复的位置在屏幕可见范围内
            self.setGeometry(x, y, width, height)

            # 恢复后检查并修正屏幕外位置
            screen = QApplication.primaryScreen()
            if screen:
                screen_rect = screen.availableGeometry()
                new_x = max(screen_rect.x() - width + 100, min(x, screen_rect.x() + screen_rect.width() - 100))
                new_y = max(screen_rect.y(), min(y, screen_rect.y() + screen_rect.height() - 100))
                if new_x != x or new_y != y:
                    self.move(new_x, new_y)
        else:
            self.resize(width, height)

        # 异步刷新设置页
        QTimer.singleShot(500, self._refresh_settings_page)
        QTimer.singleShot(500, self._refresh_task_list)

    def closeEvent(self, event) -> None:
        """
        窗口关闭事件。

        保存窗口状态和设置，检测未导出数据时弹窗提醒，
        等待所有后台工作线程退出后再关闭进程。
        """
        # 保存窗口状态
        settings = self._system_service.get_settings()
        settings["window"] = {
            "width": self.width(),
            "height": self.height(),
            "x": self.x(),
            "y": self.y(),
        }
        self._system_service.update_settings(settings)

        # 检查未导出的数据
        unexported = self._data_service.get_unexported_tasks()
        if unexported:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("数据未导出")
            msg_box.setText(
                f"当前有 {len(unexported)} 个任务的数据未导出，"
                "关闭后数据将丢失。是否继续关闭？"
            )
            msg_box.setIcon(QMessageBox.Icon.Warning)
            yes_btn = msg_box.addButton("继续关闭", QMessageBox.ButtonRole.YesRole)
            msg_box.addButton("取消关闭", QMessageBox.ButtonRole.NoRole)
            msg_box.exec()
            if msg_box.clickedButton() != yes_btn:
                event.ignore()
                return

        # 记录本次运行时间
        elapsed = int(time.time() - self._system_service._start_time)
        self._stats_service.add_run_seconds(elapsed)

        # 第一步：断开所有工作线程的信号连接，防止关闭过程中触发 UI 更新
        for task_name, worker in list(self._task_service._workers.items()):
            try:
                worker.progress.disconnect()
                worker.complete.disconnect()
                worker.error.disconnect()
                worker.log.disconnect()
            except (TypeError, RuntimeError):
                pass  # 信号可能已断开

        # 第二步：发送停止信号给所有正在运行/暂停的任务
        for task_name, task in list(self._task_service._tasks.items()):
            if task.status in (TaskStatus.RUNNING, TaskStatus.PAUSED):
                self._task_service.stop_task(task_name, complete_early=True)

        # 第三步：等待所有工作线程退出（最多等待 8 秒）
        max_wait_ms = 8000
        for task_name, worker in list(self._task_service._workers.items()):
            if worker.isRunning():
                logger.info(f"等待工作线程 [{task_name}] 退出...")
                if not worker.wait(min(max_wait_ms, 3000)):
                    logger.warning(f"工作线程 [{task_name}] 未能在 3 秒内退出，强制终止")
                    worker.terminate()
                    worker.wait(2000)  # 等待 terminate 生效
                max_wait_ms -= 3000
                if max_wait_ms <= 0:
                    # 超时保护：不再等待剩余线程，直接强制终止
                    break

        # 第四步：强制终止剩余未退出的线程
        for task_name, worker in list(self._task_service._workers.items()):
            if worker.isRunning():
                logger.warning(f"工作线程 [{task_name}] 超时未退出，强制终止")
                worker.terminate()
                worker.wait(1000)

        # 清除缓存的评论图片
        self._clear_cached_images()

        shutdown_logger()
        event.accept()

    def _clear_cached_images(self) -> None:
        """
        清除缓存的评论图片目录。

        软件关闭时自动清理，释放磁盘空间。
        已导出的文件不受影响。
        """
        import shutil
        from src.utils.paths import get_images_dir

        images_dir = get_images_dir()
        if not images_dir.exists():
            return

        try:
            count = sum(1 for _ in images_dir.rglob("*") if _.is_file())
            shutil.rmtree(images_dir)
            logger.info(f"已清除缓存图片: {count} 个文件")
        except OSError as e:
            logger.warning(f"清除缓存图片失败: {e}")

    def quit_app(self) -> None:
        """退出应用程序（从托盘菜单）。

        先调用 close() 触发 closeEvent 中的清理逻辑，
        再调用 QApplication.quit() 确保事件循环退出。
        """
        self.close()
        # closeEvent 已处理线程清理，此处确保进程退出
        QApplication.quit()
        # 使用 os._exit(0) 作为兜底，防止 PyInstaller 打包后
        # 因残留的非 daemon 线程导致进程无法退出
        import os as _os
        QTimer.singleShot(3000, lambda: _os._exit(0))
