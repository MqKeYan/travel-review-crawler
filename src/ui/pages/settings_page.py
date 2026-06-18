"""
模块名称：系统设置页面

功能说明：
    - 全局配置管理
    - 通知设置（桌面弹窗、声音、PushPlus）
    - 代理设置
    - 导出默认设置
    - 系统信息显示
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QGroupBox,
    QFormLayout, QFileDialog, QScrollArea,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


class SettingsPage(QWidget):
    """
    系统设置页面。

    提供全局配置的查看和修改。

    Signal:
        settings_updated(dict): 设置被更新
        proxy_test_requested(str): 测试代理
    """

    settings_updated = Signal(dict)
    proxy_test_requested = Signal(str)
    clear_data_requested = Signal()
    reset_settings_requested = Signal()
    reinitialize_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化设置页面 UI（可滚动）"""
        # 外层布局：全屏 + 滚动条
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        # 内容容器
        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # ---- 标题 ----
        title = QLabel("系统设置")
        title.setFont(QFont("微软雅黑", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        # ---- 代理设置 ----
        proxy_group = QGroupBox("代理设置")
        proxy_form = QFormLayout()
        proxy_form.setSpacing(10)

        # 第一行：启用复选框 + 测试按钮 + 状态
        proxy_row1 = QHBoxLayout()
        proxy_row1.setSpacing(12)

        self._proxy_enable_cb = QCheckBox("启用 HTTP/HTTPS 代理")
        proxy_row1.addWidget(self._proxy_enable_cb)

        test_proxy_btn = QPushButton("测试代理")
        test_proxy_btn.setObjectName("secondaryBtn")
        test_proxy_btn.setMinimumWidth(90)
        test_proxy_btn.clicked.connect(self._on_test_proxy)
        proxy_row1.addWidget(test_proxy_btn)

        self._proxy_status = QLabel("")
        self._proxy_status.setStyleSheet("color: #999999; font-size: 12px;")
        proxy_row1.addWidget(self._proxy_status)
        proxy_row1.addStretch()
        proxy_form.addRow(proxy_row1)

        self._proxy_http_input = QLineEdit()
        self._proxy_http_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_form.addRow("HTTP 代理:", self._proxy_http_input)

        self._proxy_https_input = QLineEdit()
        self._proxy_https_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_form.addRow("HTTPS 代理:", self._proxy_https_input)

        proxy_group.setLayout(proxy_form)
        layout.addWidget(proxy_group)

        # ---- 导出默认设置 ----
        export_group = QGroupBox("导出默认设置")
        export_form = QFormLayout()

        self._default_path_input = QLineEdit()
        self._default_path_input.setPlaceholderText("留空使用默认导出目录")
        browse_btn = QPushButton("浏览...")
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self._on_browse_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self._default_path_input)
        path_layout.addWidget(browse_btn)
        export_form.addRow("默认保存路径:", path_layout)

        export_group.setLayout(export_form)
        layout.addWidget(export_group)

        # ---- 数据管理 ----
        mgmt_group = QGroupBox("数据管理")
        mgmt_layout = QVBoxLayout()
        mgmt_layout.setSpacing(10)

        # 按钮行
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

        reinit_btn = QPushButton("重新初始化")
        reinit_btn.setObjectName("secondaryBtn")
        reinit_btn.setToolTip("清空累计统计、任务记录、Cookie 和设置，恢复为首次使用状态")
        reinit_btn.clicked.connect(self.reinitialize_requested.emit)
        btn_row.addWidget(reinit_btn)

        btn_row.addStretch()
        mgmt_layout.addLayout(btn_row)

        mgmt_group.setLayout(mgmt_layout)
        layout.addWidget(mgmt_group)

        # ---- 保存按钮 ----
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        # 弹性占位
        layout.addStretch()

        content.setLayout(layout)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)

    def load_settings(self, settings: dict) -> None:
        """
        加载设置到 UI 控件。

        Args:
            settings: 设置字典
        """
        proxy = settings.get("proxy", {})
        self._proxy_enable_cb.setChecked(proxy.get("enabled", False))
        self._proxy_http_input.setText(proxy.get("http", ""))
        self._proxy_https_input.setText(proxy.get("https", ""))

        export = settings.get("export", {})
        self._default_path_input.setText(export.get("default_path", ""))

    def _on_browse_path(self) -> None:
        """浏览目录选择器"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if dir_path:
            self._default_path_input.setText(dir_path)

    def _on_test_proxy(self) -> None:
        """测试代理按钮"""
        proxy_url = self._proxy_http_input.text().strip()
        if proxy_url:
            self._proxy_status.setText("测试中...")
            self._proxy_status.setStyleSheet("color: #FFAB00;")
            self.proxy_test_requested.emit(proxy_url)

    def set_proxy_test_result(self, success: bool) -> None:
        """设置代理测试结果"""
        if success:
            self._proxy_status.setText("代理可用")
            self._proxy_status.setStyleSheet("color: #00E676;")
        else:
            self._proxy_status.setText("代理不可用")
            self._proxy_status.setStyleSheet("color: #FF5252;")

    def _on_save(self) -> None:
        """保存设置按钮"""
        settings = {
            "proxy": {
                "enabled": self._proxy_enable_cb.isChecked(),
                "http": self._proxy_http_input.text().strip(),
                "https": self._proxy_https_input.text().strip(),
            },
            "export": {
                "default_path": self._default_path_input.text().strip(),
            },
        }
        self.settings_updated.emit(settings)
