"""
模块名称：新建爬取任务页面

功能说明：
    - 表单页面，用户配置爬取任务的各项参数
    - 包含 Cookie 获取按钮和切换
    - 包含通知设置（每个任务独立）
    - 导出统一在数据页面进行
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QScrollArea, QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QFont, QIntValidator

from src.models.task import (
    TaskConfig, ScrapeConfig, FilterConfig,
    ExportConfig, NotifyConfig, NotifySetting,
)
from src.utils.paths import get_cookie_platform_dir


def normalize_date(date_str: str) -> str:
    text = date_str.strip()
    if not text:
        return ""
    for sep in ("/", "."):
        text = text.replace(sep, "-")
    return text


class _SelectAllLineEdit(QLineEdit):
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.selectAll()


class _SiteComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class CreateTaskPage(QWidget):
    task_created = Signal(TaskConfig)
    get_cookie = Signal(str)
    cancel = Signal()

    @staticmethod
    def _label(text: str) -> QLabel:
        """创建与 QLineEdit 垂直 padding 一致的标签，确保文字基线对齐"""
        lbl = QLabel(text)
        lbl.setStyleSheet("padding: 10px 0px;")
        return lbl

    def __init__(self, sites: list[dict], parent=None):
        super().__init__(parent)
        self._sites = sites
        self._cookie_site: str = ""
        self._has_cookie: bool = False
        self._existing_task_names: set[str] = set()
        self._defaults: dict = {}
        self._setup_ui()

    def set_existing_tasks(self, task_names: list[str]) -> None:
        self._existing_task_names = set(task_names)

    def set_defaults(self, defaults: dict) -> None:
        self._defaults = dict(defaults) if defaults else {}

    def reset_form(self) -> None:
        self._scroll.verticalScrollBar().setValue(0)
        d = self._defaults
        self._name_input.clear()
        self._name_input.setStyleSheet("")
        self._name_input.setPlaceholderText("例如: 黄山风景区评论")
        if self._site_combo.count() > 0:
            self._site_combo.setCurrentIndex(0)
        self._url_input.clear()
        self._url_input.setStyleSheet("")
        self._url_input.setPlaceholderText("输入完整URL或景点ID编号")
        max_count = d.get("default_max_count") or 0
        self._max_count_input.setText(str(max_count) if max_count else "")
        max_pages = d.get("default_max_pages") or 0
        self._max_pages_input.setText(str(max_pages) if max_pages else "")
        self._delay_spin.setValue(d.get("default_delay_seconds") or 2)
        self._date_from.clear()
        self._date_to.clear()
        self._filter_images_cb.setChecked(bool(d.get("default_remove_images")))
        self._filter_emoji_cb.setChecked(bool(d.get("default_remove_emoji")))
        self._filter_pure_emoji_cb.setChecked(bool(d.get("default_skip_pure_emoji")))
        self._filter_ad_cb.setChecked(bool(d.get("default_ad_filter")))
        self._notify_popup_cb.setChecked(False)
        self._notify_sound_cb.setChecked(False)
        self._notify_pushplus_input.clear()
        self._cookie_switch.setCurrentIndex(0)
        self._cookie_label.setText("未使用 Cookie")
        self._cookie_label.setStyleSheet("color: #555555; font-size: 12px;")
        self._has_cookie = False

    def _setup_ui(self) -> None:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        title = QLabel("新建爬取任务")
        title.setFont(QFont("微软雅黑", 24, QFont.Weight.Bold))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ---- 基本信息 ----
        basic_group = QGroupBox("基本信息")
        basic_form = QFormLayout()
        basic_form.setSpacing(12)

        self._name_input = _SelectAllLineEdit()
        self._name_input.setPlaceholderText("例如: 黄山风景区评论")
        basic_form.addRow(self._label("任务名称:"), self._name_input)

        self._site_combo = _SiteComboBox()
        for site in self._sites:
            self._site_combo.addItem(
                site.get("display_name", site["name"]),
                site["name"]
            )
        self._site_combo.currentIndexChanged.connect(self._on_site_changed)
        if self._sites:
            self._cookie_site = self._sites[0]["name"]
        basic_form.addRow(self._label("目标网站:"), self._site_combo)

        self._url_input = _SelectAllLineEdit()
        self._url_input.setPlaceholderText("输入完整URL或景点ID编号")
        self._url_input.textChanged.connect(self._on_url_changed)
        basic_form.addRow(self._label("目标 URL:"), self._url_input)

        # Cookie 行
        cookie_layout = QHBoxLayout()
        self._cookie_label = QLabel("未使用 Cookie")
        self._cookie_label.setStyleSheet("color: #555555; font-size: 14px;")
        self._cookie_btn = QPushButton("获取新 Cookie")
        self._cookie_btn.setObjectName("secondaryBtn")
        self._cookie_btn.clicked.connect(self._on_get_cookie)
        self._cookie_switch = QComboBox()
        self._cookie_switch.setMinimumWidth(120)
        self._cookie_switch.currentIndexChanged.connect(self._on_cookie_switched)
        cookie_layout.addWidget(QLabel("使用:"))
        cookie_layout.addWidget(self._cookie_switch)
        cookie_layout.addWidget(self._cookie_btn)
        cookie_layout.addWidget(self._cookie_label)
        cookie_layout.addStretch()
        basic_form.addRow(self._label("Cookie:"), cookie_layout)

        basic_group.setLayout(basic_form)
        layout.addWidget(basic_group)

        # ---- 爬取配置 ----
        scrape_group = QGroupBox("爬取范围")
        scrape_form = QFormLayout()
        scrape_form.setSpacing(12)

        max_count_row = QHBoxLayout()
        self._max_count_input = _SelectAllLineEdit()
        self._max_count_input.setPlaceholderText("不限")
        self._max_count_input.setValidator(QIntValidator(0, 99999))
        self._max_count_input.setFixedWidth(100)
        self._max_count_input.installEventFilter(self)
        max_count_row.addWidget(self._max_count_input)
        max_count_row.addWidget(QLabel("条"))
        max_count_row.addStretch()
        scrape_form.addRow(self._label("最大爬取:"), max_count_row)

        max_pages_row = QHBoxLayout()
        self._max_pages_input = _SelectAllLineEdit()
        self._max_pages_input.setPlaceholderText("不限")
        self._max_pages_input.setValidator(QIntValidator(0, 9999))
        self._max_pages_input.setFixedWidth(100)
        self._max_pages_input.installEventFilter(self)
        max_pages_row.addWidget(self._max_pages_input)
        max_pages_row.addWidget(QLabel("页"))
        max_pages_row.addStretch()
        scrape_form.addRow(self._label("最大页数:"), max_pages_row)

        delay_row = QHBoxLayout()
        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(1, 30)
        self._delay_spin.setValue(2)
        self._delay_spin.setToolTip("每次请求的等待间隔，越大越慢但越安全")
        self._delay_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._delay_spin.installEventFilter(self)
        delay_row.addWidget(self._delay_spin)
        delay_row.addWidget(QLabel("秒"))
        delay_row.addStretch()
        scrape_form.addRow(self._label("请求间隔:"), delay_row)

        date_layout = QHBoxLayout()
        self._date_from = _SelectAllLineEdit()
        self._date_from.setPlaceholderText("起始日期 (可选)")
        self._date_to = _SelectAllLineEdit()
        self._date_to.setPlaceholderText("结束日期 (可选)")
        date_layout.addWidget(QLabel("从"))
        date_layout.addWidget(self._date_from)
        date_layout.addWidget(QLabel("到"))
        date_layout.addWidget(self._date_to)
        scrape_form.addRow(self._label("时间范围:"), date_layout)

        scrape_group.setLayout(scrape_form)
        layout.addWidget(scrape_group)

        # ---- 过滤配置 ----
        filter_group = QGroupBox("内容过滤")
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(8)

        self._filter_images_cb = QCheckBox("移除图片标签和链接")
        self._filter_images_cb.setChecked(False)
        filter_layout.addWidget(self._filter_images_cb)

        self._filter_emoji_cb = QCheckBox("移除 emoji 字符")
        self._filter_emoji_cb.setChecked(False)
        filter_layout.addWidget(self._filter_emoji_cb)

        self._filter_pure_emoji_cb = QCheckBox("跳过纯表情评论（无文字内容）")
        self._filter_pure_emoji_cb.setChecked(False)
        filter_layout.addWidget(self._filter_pure_emoji_cb)

        self._filter_ad_cb = QCheckBox("广告/敏感词过滤")
        self._filter_ad_cb.setChecked(False)
        filter_layout.addWidget(self._filter_ad_cb)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # ---- 通知设置 ----
        notify_group = QGroupBox("通知设置")
        notify_form = QFormLayout()
        notify_form.setSpacing(10)

        self._notify_popup_cb = QCheckBox("任务完成时桌面弹窗")
        self._notify_popup_cb.setChecked(False)
        notify_form.addRow(self._label("桌面通知:"), self._notify_popup_cb)

        self._notify_sound_cb = QCheckBox("任务完成时播放提示音")
        self._notify_sound_cb.setChecked(False)
        notify_form.addRow(self._label("声音提示:"), self._notify_sound_cb)

        self._notify_pushplus_input = _SelectAllLineEdit()
        self._notify_pushplus_input.setPlaceholderText("输入 PushPlus Token（留空不推送）")
        notify_form.addRow(self._label("PushPlus Token:"), self._notify_pushplus_input)

        notify_group.setLayout(notify_form)
        layout.addWidget(notify_group)

        # ---- 操作按钮 ----
        btn_layout = QHBoxLayout()

        self._create_btn = QPushButton("创建任务")
        self._create_btn.clicked.connect(self._on_create)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.cancel.emit)

        btn_layout.addWidget(self._create_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        content.setLayout(layout)
        self._scroll.setWidget(content)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._scroll)
        self.setLayout(main_layout)

        self._refresh_cookie_list()

    # ==================== Cookie 管理 ====================

    def _refresh_cookie_list(self) -> None:
        self._cookie_switch.clear()
        self._cookie_switch.addItem("-- 不使用 --", "")
        if self._cookie_site:
            platform_dir = get_cookie_platform_dir(self._cookie_site)
            if platform_dir.exists():
                for f in sorted(platform_dir.glob("*.json")):
                    name = f.stem
                    self._cookie_switch.addItem(name, name)
        if self._has_cookie and self._cookie_site:
            idx = self._cookie_switch.findData(self._cookie_site)
            if idx >= 0:
                self._cookie_switch.setCurrentIndex(idx)

    def _on_site_changed(self) -> None:
        site = self._site_combo.currentData()
        self._cookie_site = site
        self._has_cookie = False
        self._cookie_label.setText("未使用 Cookie")
        self._cookie_label.setStyleSheet("color: #555555; font-size: 12px;")
        self._refresh_cookie_list()

    def _on_url_changed(self, text: str) -> None:
        if not text or not text.startswith("http"):
            return
        from urllib.parse import urlparse
        try:
            host = urlparse(text).netloc.lower()
        except Exception:
            return
        for idx in range(self._site_combo.count()):
            site_name = self._site_combo.itemData(idx)
            site_info = next((s for s in self._sites if s["name"] == site_name), None)
            if site_info:
                domain = site_info.get("domain", "")
                if domain and host.endswith(domain.lstrip(".")):
                    if self._site_combo.currentIndex() != idx:
                        self._site_combo.setCurrentIndex(idx)
                    return

    def _on_cookie_switched(self) -> None:
        name = self._cookie_switch.currentData()
        if name:
            self._cookie_site = name
            self._has_cookie = True
            self._cookie_label.setText(f"已选择: {name}")
            self._cookie_label.setStyleSheet("color: #00A844; font-size: 12px;")
        else:
            self._has_cookie = False
            self._cookie_label.setText("未使用 Cookie")
            self._cookie_label.setStyleSheet("color: #555555; font-size: 12px;")

    def _get_selected_cookie(self) -> str:
        name = self._cookie_switch.currentData()
        return name if name else ""

    def _on_get_cookie(self) -> None:
        site = self._site_combo.currentData()
        self.get_cookie.emit(site)

    def set_cookie_status(self, success: bool) -> None:
        if success:
            self._has_cookie = True
            self._cookie_label.setText("Cookie 已获取")
            self._cookie_label.setStyleSheet("color: #00A844; font-size: 12px;")
            self._refresh_cookie_list()
        else:
            self._has_cookie = False
            self._cookie_label.setText("获取失败")
            self._cookie_label.setStyleSheet("color: #C62828; font-size: 12px;")

    # ==================== 创建任务 ====================

    def _parse_int(self, text: str) -> int | None:
        text = text.strip()
        if not text:
            return None
        try:
            val = int(text)
            return val if val > 0 else None
        except ValueError:
            return None

    def _on_create(self) -> None:
        task_name = self._name_input.text().strip()
        if not task_name:
            self._name_input.setFocus()
            self._name_input.setPlaceholderText("请输入任务名称！")
            self._name_input.setStyleSheet("border-color: #FF5252;")
            return

        if task_name in self._existing_task_names:
            self._name_input.setFocus()
            self._name_input.selectAll()
            self._name_input.setStyleSheet("border-color: #FF5252;")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "名称重复", f"任务「{task_name}」已存在，请使用其他名称。")
            return

        self._name_input.setStyleSheet("")

        site = self._site_combo.currentData()
        if not site:
            self._site_combo.setFocus()
            return

        target_url = self._url_input.text().strip()
        if not target_url:
            self._url_input.setFocus()
            self._url_input.setPlaceholderText("请输入目标 URL 或 ID")
            self._url_input.setStyleSheet("border-color: #FF5252;")
            return
        self._url_input.setStyleSheet("")

        if not target_url.startswith("http"):
            site_info = next((s for s in self._sites if s["name"] == site), None)
            template = site_info.get("url_template", "") if site_info else ""
            if template:
                target_url = template.replace("{id}", target_url)
            else:
                self._url_input.setFocus()
                self._url_input.setPlaceholderText("该网站不支持ID输入，请输入完整URL")
                self._url_input.setStyleSheet("border-color: #FF5252;")
                return

        config = TaskConfig(
            task_name=task_name,
            site=site,
            target_url=target_url,
            cookie_file=self._get_selected_cookie(),
            scrape_config=ScrapeConfig(
                max_count=self._parse_int(self._max_count_input.text()),
                max_pages=self._parse_int(self._max_pages_input.text()),
                date_from=normalize_date(self._date_from.text()) or None,
                date_to=normalize_date(self._date_to.text()) or None,
                delay_seconds=self._delay_spin.value(),
            ),
            filter_config=FilterConfig(
                remove_images=self._filter_images_cb.isChecked(),
                remove_emoji=self._filter_emoji_cb.isChecked(),
                skip_pure_emoji=self._filter_pure_emoji_cb.isChecked(),
                ad_filter=self._filter_ad_cb.isChecked(),
            ),
            export_config=ExportConfig(formats=[]),
            notify_config=NotifyConfig(
                on_complete=NotifySetting(
                    desktop_popup=self._notify_popup_cb.isChecked(),
                    sound=self._notify_sound_cb.isChecked(),
                    pushplus_token=self._notify_pushplus_input.text().strip(),
                ),
                on_error=NotifySetting(
                    desktop_popup=self._notify_popup_cb.isChecked(),
                    sound=self._notify_sound_cb.isChecked(),
                    pushplus_token=self._notify_pushplus_input.text().strip(),
                ),
            ),
        )

        self.task_created.emit(config)

    def eventFilter(self, obj, event):
        if isinstance(obj, QSpinBox):
            if event.type() == QEvent.Type.Wheel:
                fw = obj.focusWidget()
                focused = obj.hasFocus() or (fw is not None and fw.hasFocus())
                if not focused:
                    event.ignore()
                    return True
            elif event.type() == QEvent.Type.FocusIn:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, obj.lineEdit().selectAll)
        elif obj in (self._max_count_input, self._max_pages_input):
            if event.type() == QEvent.Type.Wheel and obj.hasFocus():
                delta = event.angleDelta().y()
                txt = obj.text().strip()
                val = int(txt) if txt else 0
                val = max(0, val + (1 if delta > 0 else -1))
                obj.setText(str(val) if val > 0 else "")
                event.accept()
                return True
        return super().eventFilter(obj, event)
