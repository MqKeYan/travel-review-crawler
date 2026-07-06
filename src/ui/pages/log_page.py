"""
模块名称：系统记录页面

功能说明：
    - 三标签页：系统日志 / Cookie日志 / 爬虫日志
    - 日志级别过滤（INFO/WARN/ERROR/DEBUG 复选框）
    - 关键词搜索
    - 智能滚动（滚轮上滑暂停，滑到底端自动恢复）
    - 实时更新（LogService Signal 驱动）
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QLineEdit, QTabWidget, QPlainTextEdit,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor

from src.services.log_service import LogService, LogEntry, LEVEL_NAMES
from src.ui.theme.dark_forest_theme import LOG_COLORS


# 标签页配置：(标识, 标题, 过滤类别, 描述)
TAB_CONFIG = [
    ("system", "系统记录", "system", "此页显示全部系统活动记录。"),
    ("cookie", "Cookie 记录", "cookie", "此页显示 Cookie 获取、保存、加载与删除记录。"),
    ("crawler", "爬虫记录", "crawler", "此页显示爬虫任务运行、验证码求解、图片下载记录。"),
    ("export", "导出记录", "export", "此页显示数据导出任务与文件生成记录。"),
]

# 日志级别 → HTML 显示颜色，按主题区分
_LEVEL_COLORS: dict[int, str] = {
    logging.DEBUG: LOG_COLORS["dark"]["DEBUG"],
    logging.INFO: LOG_COLORS["dark"]["INFO"],
    logging.WARNING: LOG_COLORS["dark"]["WARNING"],
    logging.ERROR: LOG_COLORS["dark"]["ERROR"],
    logging.CRITICAL: LOG_COLORS["dark"]["CRITICAL"],
}

# 最多在 UI 中显示的行数（内存缓冲可更大，UI 只显示最近的）
MAX_DISPLAY_LINES = 5000

# 滚动到底部的容差（像素），scrollbar 距底部在此范围内视为"在底部"
SCROLL_BOTTOM_TOLERANCE = 30


class _LogTextEdit(QPlainTextEdit):
    """只读日志显示区域，等宽字体，智能自动滚动"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(MAX_DISPLAY_LINES)
        self.setFont(QFont("Consolas", 12))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("logTextEdit")
        # 用户手动滚动后暂停自动滚动
        self._auto_scroll = True
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)

    def _on_scroll_value_changed(self, value: int) -> None:
        """检测用户是否滚离底部，控制自动滚动"""
        sb = self.verticalScrollBar()
        at_bottom = sb.maximum() - value <= SCROLL_BOTTOM_TOLERANCE
        self._auto_scroll = at_bottom

    def append_colored(self, entry: LogEntry) -> None:
        """追加带颜色的日志行"""
        color = _LEVEL_COLORS.get(entry.level, "#E0E0E0")
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        line = f'<span style="color:{color};">[{ts}] {entry.level_name:5s} {entry.message}</span>'

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(line)
        cursor.insertBlock()
        self.setTextCursor(cursor)

    def scroll_to_bottom(self) -> None:
        """滚动到底部"""
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    @property
    def auto_scroll(self) -> bool:
        return self._auto_scroll


class LogPage(QWidget):
    """
    系统记录页面。

    布局：
        ┌─ 标题 ──────────────────────────────┐
        ├─ 标签页 ─────────────────────────────┤
        │  [一般记录文件] [Cookie记录] [爬虫记录] │
        ├─ 工具栏（级别过滤 / 搜索）─────────────┤
        │                                       │
        │  日志显示区域（等宽字体，智能滚动）      │
        │                                       │
        └───────────────────────────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_service = LogService()
        self._current_category = "system"
        self._enabled_levels: set[int] = {logging.INFO, logging.WARNING, logging.ERROR}
        self._keyword = ""
        self._batch_timer: QTimer | None = None
        self._pending_entries: list[LogEntry] = []

        self._setup_ui()
        self._connect_signals()

    # ==================== UI 构建 ====================

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ---- 标题 ----
        title = QLabel("系统记录")
        title.setFont(QFont("微软雅黑", 24, QFont.Weight.Bold))
        title.setObjectName("pageTitle")
        title.setContentsMargins(32, 25, 32, 8)
        outer_layout.addWidget(title)

        # ---- 标签页（容器包裹，留出左右空白） ----
        tab_container = QWidget()
        tab_container_layout = QVBoxLayout()
        tab_container_layout.setContentsMargins(32, 8, 32, 8)
        tab_container_layout.setSpacing(0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("logTabWidget")
        self._tab_widget.setFont(QFont("微软雅黑", 13))

        self._log_views: dict[str, _LogTextEdit] = {}
        for key, label, category, desc in TAB_CONFIG:
            log_view = _LogTextEdit()
            self._log_views[category] = log_view
            self._tab_widget.addTab(log_view, label)

        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        tab_container_layout.addWidget(self._tab_widget)
        tab_container.setLayout(tab_container_layout)
        outer_layout.addWidget(tab_container, 1)

        # ---- 工具栏（级别过滤 / 搜索 / 统计） ----
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(32, 6, 32, 20)
        toolbar_layout.setSpacing(12)

        level_label = QLabel("级别:")
        level_label.setFont(QFont("微软雅黑", 12))
        level_label.setStyleSheet("padding: 2px 0px;")
        toolbar_layout.addWidget(level_label)

        self._level_cbs: dict[int, QCheckBox] = {}
        for level, color in [(logging.INFO, "#00E676"), (logging.WARNING, "#FFB74D"),
                              (logging.ERROR, "#EF5350"), (logging.DEBUG, "#42A5F5")]:
            name = LEVEL_NAMES.get(level, "?")
            cb = QCheckBox(name)
            cb.setFont(QFont("微软雅黑", 11))
            cb.setChecked(level in self._enabled_levels)
            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}")
            cb.toggled.connect(lambda checked, l=level: self._on_level_toggled(l, checked))
            self._level_cbs[level] = cb
            toolbar_layout.addWidget(cb)

        toolbar_layout.addSpacing(18)

        search_label = QLabel("搜索:")
        search_label.setFont(QFont("微软雅黑", 12))
        search_label.setStyleSheet("padding: 2px 0px;")
        toolbar_layout.addWidget(search_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入关键词搜索...")
        self._search_input.setFont(QFont("微软雅黑", 11))
        self._search_input.setMinimumWidth(180)
        self._search_input.setMaximumWidth(280)
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_changed)
        toolbar_layout.addWidget(self._search_input)

        toolbar_layout.addStretch()

        self._stats_label = QLabel()
        self._stats_label.setFont(QFont("微软雅黑", 11))
        self._stats_label.setTextFormat(Qt.TextFormat.RichText)
        self._stats_label.setObjectName("logStatsLabel")
        toolbar_layout.addWidget(self._stats_label)

        toolbar.setLayout(toolbar_layout)
        outer_layout.addWidget(toolbar)

        self.setLayout(outer_layout)

        # 初始加载
        self._refresh_current_view()

    # ==================== 信号连接 ====================

    def set_theme(self, theme: str) -> None:
        """切换日志颜色主题并刷新显示"""
        colors = LOG_COLORS.get(theme, LOG_COLORS["dark"])
        _LEVEL_COLORS[logging.DEBUG] = colors["DEBUG"]
        _LEVEL_COLORS[logging.INFO] = colors["INFO"]
        _LEVEL_COLORS[logging.WARNING] = colors["WARNING"]
        _LEVEL_COLORS[logging.ERROR] = colors["ERROR"]
        _LEVEL_COLORS[logging.CRITICAL] = colors["CRITICAL"]

        # 更新工具栏复选框颜色
        cb_colors = {
            logging.INFO: colors["INFO"],
            logging.WARNING: colors["WARNING"],
            logging.ERROR: colors["ERROR"],
            logging.DEBUG: colors["DEBUG"],
        }
        for level, cb in self._level_cbs.items():
            color = cb_colors.get(level, "#E0E0E0")
            cb.setStyleSheet(f"QCheckBox {{ color: {color}; }}")

        self._refresh_all_views()

    def _refresh_all_views(self) -> None:
        """刷新所有标签页视图"""
        for cat, view in self._log_views.items():
            view.clear()
            entries = self._log_service.get_entries(
                category=cat,
                levels=self._enabled_levels,
                keyword=self._keyword,
            )
            for entry in entries:
                view.append_colored(entry)

        # 恢复当前标签页（_refresh_all_views 会清除所有视图，需要把当前页再刷新一遍）
        # 实际上上面的循环已经处理了当前页，所以只需更新统计
        self._update_stats()

    # ==================== 信号连接 ====================

    def _connect_signals(self) -> None:
        """连接 LogService 信号"""
        self._log_service.entry_added.connect(self._on_entry_added)

        # 批量刷新：80ms 合并一次，兼顾实时性与性能
        self._batch_timer = QTimer(self)
        self._batch_timer.setInterval(80)
        self._batch_timer.timeout.connect(self._flush_pending)
        self._batch_timer.start()

    # ==================== 日志更新 ====================

    def _on_entry_added(self, entry: LogEntry) -> None:
        self._pending_entries.append(entry)
        # 少量日志立即刷新，大量日志由定时器批量处理避免 UI 卡顿
        if len(self._pending_entries) <= 3:
            self._flush_pending()

    def _flush_pending(self) -> None:
        if not self._pending_entries:
            return

        for entry in self._pending_entries:
            # 独立判断每个视图，不因当前标签页过滤（保证切标签页时历史日志不丢失）
            for cat, view in self._log_views.items():
                if not entry.matches_category(cat):
                    continue
                if entry.level not in self._enabled_levels:
                    continue
                kw = self._keyword.lower().strip()
                if kw and kw not in entry.message.lower():
                    continue
                view.append_colored(entry)

        self._pending_entries.clear()

        # 更新统计
        self._update_stats()

        # 当前视图如果在底部则自动滚到底
        current_view = self._log_views.get(self._current_category)
        if current_view and current_view.auto_scroll:
            current_view.scroll_to_bottom()

    # ==================== 标签页切换 ====================

    def _on_tab_changed(self, index: int) -> None:
        if 0 <= index < len(TAB_CONFIG):
            self._current_category = TAB_CONFIG[index][2]
            self._refresh_current_view()

    # ==================== 级别过滤 ====================

    def _on_level_toggled(self, level: int, checked: bool) -> None:
        if checked:
            self._enabled_levels.add(level)
        else:
            self._enabled_levels.discard(level)
        self._refresh_current_view()

    # ==================== 关键词搜索 ====================

    def _on_search_changed(self, text: str) -> None:
        self._keyword = text.strip()
        self._refresh_current_view()

    # ==================== 内部方法 ====================

    def _refresh_current_view(self) -> None:
        view = self._log_views.get(self._current_category)
        if not view:
            return

        view.clear()
        entries = self._log_service.get_entries(
            category=self._current_category,
            levels=self._enabled_levels,
            keyword=self._keyword,
        )

        for entry in entries:
            view.append_colored(entry)

        self._update_stats()

        # 刷新后滚动到底部
        view.scroll_to_bottom()

    def _update_stats(self) -> None:
        """更新工具栏中的日志统计"""
        entries = self._log_service.get_entries(category=self._current_category)
        counts: dict[int, int] = {}
        for e in entries:
            counts[e.level] = counts.get(e.level, 0) + 1

        colors = {
            logging.ERROR: _LEVEL_COLORS[logging.ERROR],
            logging.WARNING: _LEVEL_COLORS[logging.WARNING],
            logging.INFO: _LEVEL_COLORS[logging.INFO],
            logging.DEBUG: _LEVEL_COLORS[logging.DEBUG],
        }
        parts = []
        for level in [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]:
            c = counts.get(level, 0)
            name = LEVEL_NAMES.get(level, "?")
            color = colors.get(level, "#E0E0E0")
            parts.append(f'<span style="color:{color};">{name}:{c}</span>')

        self._stats_label.setText("&nbsp;&nbsp;&nbsp;&nbsp;" + "&nbsp;&nbsp;&nbsp;&nbsp;".join(parts))
