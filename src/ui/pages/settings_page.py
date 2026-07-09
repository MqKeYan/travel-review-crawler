"""
模块名称：系统设置页面

功能说明：
    - 全局配置管理
    - 界面主题、代理、导出默认设置
    - 自动保存（变更即生效）
    - 数据管理（清空/还原/重新初始化）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QGroupBox,
    QFormLayout, QFileDialog, QScrollArea, QComboBox, QSpinBox,
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QFont, QIntValidator

from src.ui.theme.dark_forest_theme import THEME_DISPLAY_NAMES


class _SelectAllLineEdit(QLineEdit):
    """双击全选文本"""
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.selectAll()


class _ThemeComboBox(QComboBox):
    """无条件禁用滚轮的主题下拉框"""
    def wheelEvent(self, event):
        event.ignore()


class SettingsPage(QWidget):
    """系统设置页面，变更自动保存。"""

    settings_updated = Signal(dict)
    proxy_test_requested = Signal(str)
    theme_changed = Signal(str)
    clear_data_requested = Signal()
    reset_settings_requested = Signal()
    reinitialize_requested = Signal()

    @staticmethod
    def _label(text: str) -> QLabel:
        """创建与 QLineEdit 垂直 padding 一致的标签，确保文字基线对齐"""
        lbl = QLabel(text)
        lbl.setStyleSheet("padding: 10px 0px;")
        return lbl

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 25, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 0, 32, 20)
        layout.setSpacing(16)

        # ---- 标题 ----
        title = QLabel("系统设置")
        title.setFont(QFont("微软雅黑", 24, QFont.Weight.Bold))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ---- 界面主题 ----
        theme_group = QGroupBox("界面主题")
        theme_layout = QFormLayout()
        theme_layout.setSpacing(10)

        self._theme_combo = _ThemeComboBox()
        self._theme_combo.setMinimumWidth(200)
        for key, display in THEME_DISPLAY_NAMES.items():
            self._theme_combo.addItem(display, key)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addRow(self._label("选择主题:"), self._theme_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # ---- 参数默认值 ----
        crawl_group = QGroupBox("任务参数默认值")
        crawl_form = QFormLayout()
        crawl_form.setSpacing(10)

        count_row = QHBoxLayout()
        self._crawl_max_count = _SelectAllLineEdit()
        self._crawl_max_count.setPlaceholderText("不限")
        self._crawl_max_count.setValidator(QIntValidator(0, 99999))
        self._crawl_max_count.setFixedWidth(100)
        self._crawl_max_count.installEventFilter(self)
        count_row.addWidget(self._crawl_max_count)
        count_row.addWidget(QLabel("条"))
        count_row.addStretch()
        crawl_form.addRow(self._label("默认爬取条数:"), count_row)

        pages_row = QHBoxLayout()
        self._crawl_max_pages = _SelectAllLineEdit()
        self._crawl_max_pages.setPlaceholderText("不限")
        self._crawl_max_pages.setValidator(QIntValidator(0, 9999))
        self._crawl_max_pages.setFixedWidth(100)
        self._crawl_max_pages.installEventFilter(self)
        pages_row.addWidget(self._crawl_max_pages)
        pages_row.addWidget(QLabel("页"))
        pages_row.addStretch()
        crawl_form.addRow(self._label("默认最大页数:"), pages_row)

        delay_row = QHBoxLayout()
        self._crawl_delay = QSpinBox()
        self._crawl_delay.setRange(1, 30)
        self._crawl_delay.setValue(2)
        self._crawl_delay.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._crawl_delay.installEventFilter(self)
        # 监听内部输入框的鼠标事件，实现点击空白/双击全选
        self._crawl_delay.lineEdit().installEventFilter(self)
        delay_row.addWidget(self._crawl_delay)
        delay_row.addWidget(QLabel("秒"))
        delay_row.addStretch()
        crawl_form.addRow(self._label("默认请求间隔:"), delay_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(16)
        self._crawl_filter_images = QCheckBox("移除图片")
        self._crawl_filter_emoji = QCheckBox("移除Emoji")
        self._crawl_filter_pure_emoji = QCheckBox("跳过纯表情")
        self._crawl_filter_ad = QCheckBox("广告过滤")
        filter_row.addWidget(self._crawl_filter_images)
        filter_row.addWidget(self._crawl_filter_emoji)
        filter_row.addWidget(self._crawl_filter_pure_emoji)
        filter_row.addWidget(self._crawl_filter_ad)
        filter_row.addStretch()
        filter_label = QLabel("默认过滤:")
        filter_label.setStyleSheet("padding: 2px 0px;")  # 与 QCheckBox 自然高度对齐
        crawl_form.addRow(filter_label, filter_row)

        crawl_group.setLayout(crawl_form)
        layout.addWidget(crawl_group)

        # ---- 默认通知设置 ----
        notify_group = QGroupBox("默认通知设置")
        notify_form = QFormLayout()
        notify_form.setSpacing(10)

        notify_check_row = QHBoxLayout()
        notify_check_row.setSpacing(16)
        self._notify_popup_cb = QCheckBox("桌面弹窗")
        self._notify_sound_cb = QCheckBox("声音提示")
        notify_check_row.addWidget(self._notify_popup_cb)
        notify_check_row.addWidget(self._notify_sound_cb)
        notify_check_row.addStretch()
        notify_form.addRow(self._label("完成通知:"), notify_check_row)

        self._notify_pushplus = _SelectAllLineEdit()
        self._notify_pushplus.setPlaceholderText("输入 PushPlus Token（留空不推送）")
        notify_form.addRow(self._label("PushPlus Token:"), self._notify_pushplus)

        notify_group.setLayout(notify_form)
        layout.addWidget(notify_group)

        # ---- 代理设置 ----
        proxy_group = QGroupBox("代理设置")
        proxy_form = QFormLayout()
        proxy_form.setSpacing(10)

        proxy_row1 = QHBoxLayout()
        proxy_row1.setSpacing(12)

        self._proxy_enable_cb = QCheckBox("启用 HTTP/HTTPS 代理")
        proxy_row1.addWidget(self._proxy_enable_cb)

        self._proxy_status = QLabel("")
        self._proxy_status.setObjectName("settingsStatusHint")
        proxy_row1.addWidget(self._proxy_status)
        proxy_row1.addStretch()
        proxy_form.addRow(proxy_row1)

        self._proxy_http_input = _SelectAllLineEdit()
        self._proxy_http_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_form.addRow(self._label("HTTP 代理:"), self._proxy_http_input)

        self._proxy_https_input = _SelectAllLineEdit()
        self._proxy_https_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_form.addRow(self._label("HTTPS 代理:"), self._proxy_https_input)

        # 测试代理按钮：底部居中
        test_row = QHBoxLayout()
        test_row.addStretch()
        test_proxy_btn = QPushButton("测试代理")
        test_proxy_btn.setObjectName("secondaryBtn")
        test_proxy_btn.setFont(QFont("微软雅黑", 13))
        test_proxy_btn.clicked.connect(self._on_test_proxy)
        test_row.addWidget(test_proxy_btn)
        test_row.addStretch()
        proxy_form.addRow(test_row)

        proxy_group.setLayout(proxy_form)
        layout.addWidget(proxy_group)

        # ---- 导出默认设置 ----
        export_group = QGroupBox("导出默认设置")
        export_form = QFormLayout()

        self._default_path_input = _SelectAllLineEdit()
        self._default_path_input.setPlaceholderText("留空则默认使用软件目录的exports文件夹")
        browse_btn = QPushButton("浏览...")
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.setStyleSheet("QPushButton#secondaryBtn { min-height: 0px; padding: 11px 14px; }")
        browse_btn.clicked.connect(self._on_browse_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self._default_path_input)
        path_layout.addWidget(browse_btn)
        export_form.addRow(self._label("默认保存路径:"), path_layout)

        export_group.setLayout(export_form)
        layout.addWidget(export_group)

        # ---- 数据管理 ----
        mgmt_group = QGroupBox("数据管理")
        mgmt_layout = QVBoxLayout()
        mgmt_layout.setSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        clear_data_btn = QPushButton("清空数据")
        clear_data_btn.setObjectName("secondaryBtn")
        clear_data_btn.setToolTip("清空首页显示的累计统计数据")
        clear_data_btn.clicked.connect(self.clear_data_requested.emit)
        btn_row.addWidget(clear_data_btn)

        reset_btn = QPushButton("还原设置")
        reset_btn.setObjectName("secondaryBtn")
        reset_btn.setToolTip("将所有设置恢复为默认值")
        reset_btn.clicked.connect(self.reset_settings_requested.emit)
        btn_row.addWidget(reset_btn)

        reinit_btn = QPushButton("初始化")
        reinit_btn.setObjectName("secondaryBtn")
        reinit_btn.setToolTip("清空累计统计、任务记录、Cookie 和设置，恢复为首次使用状态")
        reinit_btn.clicked.connect(self.reinitialize_requested.emit)
        btn_row.addWidget(reinit_btn)

        btn_row.addStretch()
        mgmt_layout.addLayout(btn_row)

        mgmt_group.setLayout(mgmt_layout)
        layout.addWidget(mgmt_group)

        layout.addStretch()

        content.setLayout(layout)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)

        # ---- 连接自动保存 ----
        self._connect_auto_save()

    def _connect_auto_save(self) -> None:
        """连接所有控件的变更信号到自动保存（主题除外，已单独处理）"""
        self._crawl_max_count.textChanged.connect(self._auto_save)
        self._crawl_max_pages.textChanged.connect(self._auto_save)
        self._crawl_delay.valueChanged.connect(self._auto_save)
        self._crawl_filter_images.toggled.connect(self._auto_save)
        self._crawl_filter_emoji.toggled.connect(self._auto_save)
        self._crawl_filter_pure_emoji.toggled.connect(self._auto_save)
        self._crawl_filter_ad.toggled.connect(self._auto_save)
        self._notify_popup_cb.toggled.connect(self._auto_save)
        self._notify_sound_cb.toggled.connect(self._auto_save)
        self._notify_pushplus.textChanged.connect(self._auto_save)
        self._proxy_enable_cb.toggled.connect(self._auto_save)
        self._proxy_http_input.textChanged.connect(self._auto_save)
        self._proxy_https_input.textChanged.connect(self._auto_save)
        self._default_path_input.textChanged.connect(self._auto_save)

    def _auto_save(self) -> None:
        if self._loading:
            return
        settings = {
            "theme": self._theme_combo.currentData(),
            "crawl": {
                "default_max_count": int(self._crawl_max_count.text()) if self._crawl_max_count.text().strip() else 0,
                "default_max_pages": int(self._crawl_max_pages.text()) if self._crawl_max_pages.text().strip() else None,
                "default_delay_seconds": self._crawl_delay.value(),
                "default_remove_images": self._crawl_filter_images.isChecked(),
                "default_remove_emoji": self._crawl_filter_emoji.isChecked(),
                "default_skip_pure_emoji": self._crawl_filter_pure_emoji.isChecked(),
                "default_ad_filter": self._crawl_filter_ad.isChecked(),
            },
            "proxy": {
                "enabled": self._proxy_enable_cb.isChecked(),
                "http": self._proxy_http_input.text().strip(),
                "https": self._proxy_https_input.text().strip(),
            },
            "notify": {
                "default_desktop_popup": self._notify_popup_cb.isChecked(),
                "default_sound": self._notify_sound_cb.isChecked(),
                "default_pushplus_token": self._notify_pushplus.text().strip(),
            },
            "export": {
                "default_path": self._default_path_input.text().strip(),
            },
        }
        self.settings_updated.emit(settings)

    def load_settings(self, settings: dict) -> None:
        self._loading = True
        theme = settings.get("theme", "dark")
        if theme == "dark_forest":
            theme = "dark"
        if theme not in ("dark", "light", "auto"):
            theme = "dark"
        idx = self._theme_combo.findData(theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

        proxy = settings.get("proxy", {})
        self._proxy_enable_cb.setChecked(proxy.get("enabled", False))
        self._proxy_http_input.setText(proxy.get("http", ""))
        self._proxy_https_input.setText(proxy.get("https", ""))

        crawl = settings.get("crawl", {})
        max_count = crawl.get("default_max_count", 500) or 0
        self._crawl_max_count.setText(str(max_count) if max_count else "")
        max_pages = crawl.get("default_max_pages") or 0
        self._crawl_max_pages.setText(str(max_pages) if max_pages else "")
        self._crawl_delay.setValue(crawl.get("default_delay_seconds", 2))
        self._crawl_filter_images.setChecked(crawl.get("default_remove_images", False))
        self._crawl_filter_emoji.setChecked(crawl.get("default_remove_emoji", False))
        self._crawl_filter_pure_emoji.setChecked(crawl.get("default_skip_pure_emoji", False))
        self._crawl_filter_ad.setChecked(crawl.get("default_ad_filter", False))

        notify = settings.get("notify", {})
        self._notify_popup_cb.setChecked(notify.get("default_desktop_popup", False))
        self._notify_sound_cb.setChecked(notify.get("default_sound", False))
        self._notify_pushplus.setText(notify.get("default_pushplus_token", ""))

        export = settings.get("export", {})
        self._default_path_input.setText(export.get("default_path", ""))
        self._loading = False

    def eventFilter(self, obj, event):
        if isinstance(obj, QSpinBox):
            if event.type() == QEvent.Type.Wheel:
                fw = obj.focusWidget()
                focused = obj.hasFocus() or (fw is not None and fw.hasFocus())
                if not focused:
                    event.ignore()
                    return True
        elif isinstance(obj, QLineEdit):
            # QSpinBox 内部输入框双击全选
            if event.type() == QEvent.Type.MouseButtonDblClick:
                obj.selectAll()
        elif obj in (self._crawl_max_count, self._crawl_max_pages):
            if event.type() == QEvent.Type.Wheel and obj.hasFocus():
                delta = event.angleDelta().y()
                txt = obj.text().strip()
                val = int(txt) if txt else 0
                val = max(0, val + (1 if delta > 0 else -1))
                obj.setText(str(val) if val > 0 else "")
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def _on_theme_changed(self) -> None:
        if self._loading:
            return  # 加载设置时禁止触发主题切换信号，避免重复应用
        theme = self._theme_combo.currentData()
        if theme:
            self.theme_changed.emit(theme)

    def _on_browse_path(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if dir_path:
            self._default_path_input.setText(dir_path)

    def _on_test_proxy(self) -> None:
        proxy_url = self._proxy_http_input.text().strip()
        if proxy_url:
            self._proxy_status.setText("测试中...")
            self._proxy_status.setStyleSheet("color: #E65100; font-size: 12px;")
            self.proxy_test_requested.emit(proxy_url)

    def set_proxy_test_result(self, success: bool) -> None:
        if success:
            self._proxy_status.setText("代理可用")
            self._proxy_status.setStyleSheet("color: #00A844; font-size: 12px;")
        else:
            self._proxy_status.setText("代理不可用")
            self._proxy_status.setStyleSheet("color: #C62828; font-size: 12px;")
