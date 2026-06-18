"""
模块名称：新建爬取任务页面

功能说明：
    - 表单页面，用户配置爬取任务的各项参数
    - 包含 Cookie 获取按钮和切换
    - 包含通知设置（每个任务独立）
    - 导出统一在数据页面进行

表单字段：
    - 任务名称（必填）
    - 目标网站（必选，从预设列表选择）
    - 目标 URL（必填，景区评论页面）
    - Cookie 选择（切换已保存的 Cookie / 获取新 Cookie）
    - 爬取配置（条数/页数、时间范围）
    - 过滤配置（图片/emoji/关键词）
    - 通知配置（桌面弹窗、声音、PushPlus）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QScrollArea, QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIntValidator

from src.models.task import (
    TaskConfig, ScrapeConfig, FilterConfig,
    ExportConfig, NotifyConfig, NotifySetting,
)
from src.utils.paths import get_cookies_dir


def normalize_date(date_str: str) -> str:
    """
    统一日期格式为 YYYY-MM-DD。

    支持多种分隔符:
        "2024-01-01"  → "2024-01-01"
        "2024/01/01"  → "2024-01-01"
        "2024.01.01"  → "2024-01-01"

    Args:
        date_str: 用户输入的日期字符串

    Returns:
        规范化后的日期字符串，空输入返回空字符串
    """
    text = date_str.strip()
    if not text:
        return ""
    for sep in ("/", "."):
        text = text.replace(sep, "-")
    return text


class CreateTaskPage(QWidget):
    """
    新建爬取任务页面。

    提供完整的任务配置表单。
    创建成功后通过 task_created Signal 返回 TaskConfig。

    Signal:
        task_created(TaskConfig): 任务创建成功
        get_cookie(str): 请求获取 Cookie（携带网站名）
        cancel(): 取消创建
    """

    task_created = Signal(TaskConfig)
    get_cookie = Signal(str)
    cancel = Signal()

    def __init__(self, sites: list[dict], parent=None):
        super().__init__(parent)
        self._sites = sites
        self._cookie_site: str = ""
        self._has_cookie: bool = False
        self._existing_task_names: set[str] = set()

        self._setup_ui()

    def set_existing_tasks(self, task_names: list[str]) -> None:
        """设置已存在的任务名称列表（用于查重）"""
        self._existing_task_names = set(task_names)

    def _setup_ui(self) -> None:
        """初始化表单 UI"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # ---- 标题 ----
        title = QLabel("新建爬取任务")
        title.setFont(QFont("微软雅黑", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        # ---- 基本信息 ----
        basic_group = QGroupBox("基本信息")
        basic_form = QFormLayout()
        basic_form.setSpacing(12)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("例如: 黄山风景区评论")
        basic_form.addRow("任务名称:", self._name_input)

        self._site_combo = QComboBox()
        for site in self._sites:
            self._site_combo.addItem(
                site.get("display_name", site["name"]),
                site["name"]
            )
        self._site_combo.currentIndexChanged.connect(self._on_site_changed)
        if self._sites:
            self._cookie_site = self._sites[0]["name"]
        basic_form.addRow("目标网站:", self._site_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("粘贴景区评论页面的 URL")
        basic_form.addRow("目标 URL:", self._url_input)

        # Cookie 行：切换已有 Cookie + 获取新 Cookie
        cookie_layout = QHBoxLayout()
        self._cookie_label = QLabel("未使用 Cookie")
        self._cookie_label.setStyleSheet("color: #999999; font-size: 14px;")
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
        basic_form.addRow("Cookie:", cookie_layout)

        basic_group.setLayout(basic_form)
        layout.addWidget(basic_group)

        # ---- 爬取配置 ----
        scrape_group = QGroupBox("爬取范围")
        scrape_form = QFormLayout()
        scrape_form.setSpacing(12)

        self._max_count_input = QLineEdit()
        self._max_count_input.setPlaceholderText("不限 (直接输入数字)")
        self._max_count_input.setValidator(QIntValidator(0, 99999))
        scrape_form.addRow("最大爬取(条):", self._max_count_input)

        self._max_pages_input = QLineEdit()
        self._max_pages_input.setPlaceholderText("不限 (直接输入数字)")
        self._max_pages_input.setValidator(QIntValidator(0, 9999))
        scrape_form.addRow("最大页数:", self._max_pages_input)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(1, 10)
        self._delay_spin.setValue(2)
        self._delay_spin.setSuffix(" 秒")
        self._delay_spin.setToolTip("每次请求的等待间隔，越大越慢但越安全")
        scrape_form.addRow("请求间隔:", self._delay_spin)

        date_layout = QHBoxLayout()
        self._date_from = QLineEdit()
        self._date_from.setPlaceholderText("起始日期 (可选)")
        self._date_to = QLineEdit()
        self._date_to.setPlaceholderText("结束日期 (可选)")
        date_layout.addWidget(QLabel("从"))
        date_layout.addWidget(self._date_from)
        date_layout.addWidget(QLabel("到"))
        date_layout.addWidget(self._date_to)
        scrape_form.addRow("时间范围:", date_layout)

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
        notify_form.addRow("桌面通知:", self._notify_popup_cb)

        self._notify_sound_cb = QCheckBox("任务完成时播放提示音")
        self._notify_sound_cb.setChecked(False)
        notify_form.addRow("声音提示:", self._notify_sound_cb)

        self._notify_pushplus_input = QLineEdit()
        self._notify_pushplus_input.setPlaceholderText("输入 PushPlus Token（留空不推送）")
        notify_form.addRow("PushPlus Token:", self._notify_pushplus_input)

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
        scroll.setWidget(content)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        self._refresh_cookie_list()

    # ==================== Cookie 管理 ====================

    def _refresh_cookie_list(self) -> None:
        """刷新可用 Cookie 列表（只显示文件名）"""
        self._cookie_switch.clear()
        self._cookie_switch.addItem("-- 不使用 --", "")
        cookies_dir = get_cookies_dir()
        if cookies_dir.exists():
            for f in sorted(cookies_dir.glob("*.json")):
                name = f.stem  # 文件名去掉 .json
                self._cookie_switch.addItem(name, name)
        if self._has_cookie and self._cookie_site:
            idx = self._cookie_switch.findData(self._cookie_site)
            if idx >= 0:
                self._cookie_switch.setCurrentIndex(idx)

    def _on_site_changed(self) -> None:
        """网站选择变化"""
        site = self._site_combo.currentData()
        self._cookie_site = site
        self._has_cookie = False
        self._cookie_label.setText("未使用 Cookie")
        self._cookie_label.setStyleSheet("color: #999999; font-size: 12px;")
        self._refresh_cookie_list()

    def _on_cookie_switched(self) -> None:
        """Cookie 切换"""
        name = self._cookie_switch.currentData()
        if name:
            self._cookie_site = name
            self._has_cookie = True
            self._cookie_label.setText(f"已选择: {name}")
            self._cookie_label.setStyleSheet("color: #00E676; font-size: 12px;")
        else:
            self._has_cookie = False
            self._cookie_label.setText("未使用 Cookie")
            self._cookie_label.setStyleSheet("color: #999999; font-size: 12px;")

    def _get_selected_cookie(self) -> str:
        """获取当前选中的 Cookie 文件名"""
        name = self._cookie_switch.currentData()
        return f"{name}.json" if name else ""

    def _on_get_cookie(self) -> None:
        """点击获取 Cookie 按钮"""
        site = self._site_combo.currentData()
        self.get_cookie.emit(site)

    def set_cookie_status(self, success: bool) -> None:
        """设置 Cookie 获取状态（由外部调用）"""
        if success:
            self._has_cookie = True
            self._cookie_label.setText("Cookie 已获取")
            self._cookie_label.setStyleSheet("color: #00E676; font-size: 12px;")
            self._refresh_cookie_list()
        else:
            self._has_cookie = False
            self._cookie_label.setText("获取失败")
            self._cookie_label.setStyleSheet("color: #FF5252; font-size: 12px;")

    # ==================== 创建任务 ====================

    def _parse_int(self, text: str) -> int | None:
        """将文本框内容转为整数，空或0返回 None"""
        text = text.strip()
        if not text:
            return None
        try:
            val = int(text)
            return val if val > 0 else None
        except ValueError:
            return None

    def _on_create(self) -> None:
        """创建任务按钮"""
        task_name = self._name_input.text().strip()
        if not task_name:
            self._name_input.setFocus()
            self._name_input.setPlaceholderText("请输入任务名称！")
            self._name_input.setStyleSheet("border-color: #FF5252;")
            return

        # 任务名称查重
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
            self._url_input.setPlaceholderText("请输入目标 URL！")
            self._url_input.setStyleSheet("border-color: #FF5252;")
            return
        self._url_input.setStyleSheet("")

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
            export_config=ExportConfig(
                formats=[],  # 导出统一在数据页面处理
            ),
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
