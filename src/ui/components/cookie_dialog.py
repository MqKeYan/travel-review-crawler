"""
模块名称：Cookie 获取对话框

功能说明：
    - 点击「开始获取」后自动打开浏览器 → 等待登录 → 提取 Cookie → 关闭浏览器
    - 支持自定义 Cookie 名称
    - 实时显示状态信息
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class CookieDialog(QDialog):
    """
    Cookie 获取对话框，全自动流程。

    使用方式：
        dialog = CookieDialog(site, display, parent)
        dialog.cookie_started.connect(handler)  # 用户点击开始
        dialog.show()  # 非模态显示

    Signal:
        cookie_started(str): 用户点击「开始获取」，携带 cookie_name
    """

    cookie_started = Signal(str)

    def __init__(self, site_name: str, site_display_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("获取 Cookie")
        self.setMinimumSize(480, 360)
        self.setModal(False)  # 非模态，允许后台线程更新
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._site_name = site_name
        self._site_display_name = site_display_name
        self._cookie_saved: bool = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("获取 Cookie")
        title.setFont(QFont("微软雅黑", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #00C853;")
        layout.addWidget(title)

        steps = QLabel(
            "自动获取流程：\n\n"
            "1️⃣ 输入 Cookie 名称（用于区分不同账号）\n"
            "2️⃣ 点击「开始获取」自动打开浏览器\n"
            "3️⃣ 在弹出的浏览器中登录您的账号\n"
            "4️⃣ 系统自动检测登录状态 → 提取 Cookie → 关闭浏览器"
        )
        steps.setStyleSheet("color: #E0E0E0; font-size: 13px;")
        steps.setWordWrap(True)
        layout.addWidget(steps)

        # Cookie 名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Cookie 名称:"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(f"默认: {self._site_name}")
        self._name_input.setText(self._site_name)
        self._name_input.selectAll()
        name_layout.addWidget(self._name_input)
        layout.addLayout(name_layout)

        # 目标网站
        site_layout = QHBoxLayout()
        site_layout.addWidget(QLabel("目标网站:"))
        site_label = QLabel(self._site_display_name)
        site_label.setFont(QFont("微软雅黑", 14, QFont.Weight.Bold))
        site_label.setStyleSheet("color: #00C853;")
        site_layout.addWidget(site_label)
        site_layout.addStretch()
        layout.addLayout(site_layout)

        # 状态
        self._status_label = QLabel("就绪，点击「开始获取」")
        self._status_label.setStyleSheet("color: #999999; font-size: 12px;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        # 按钮
        btn_layout = QHBoxLayout()
        self._start_btn = QPushButton("开始获取")
        self._start_btn.clicked.connect(self._on_start)
        self._close_btn = QPushButton("关闭")
        self._close_btn.setObjectName("secondaryBtn")
        self._close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self._start_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_start(self) -> None:
        """开始获取按钮"""
        cookie_name = self._name_input.text().strip() or self._site_name
        self._start_btn.setEnabled(False)
        self._name_input.setEnabled(False)
        self._close_btn.setEnabled(False)
        self._progress_bar.show()
        self.set_status("正在打开浏览器...")
        self.cookie_started.emit(cookie_name)

    def set_status(self, message: str, success: bool = True) -> None:
        """更新状态文本"""
        self._status_label.setText(message)
        if success:
            self._status_label.setStyleSheet("color: #00E676; font-size: 12px;")
            if "保存成功" in message:
                self._cookie_saved = True
                self._progress_bar.hide()
                self._close_btn.setEnabled(True)
                self._status_label.setStyleSheet("color: #00E676; font-size: 14px; font-weight: bold;")
        else:
            self._status_label.setStyleSheet("color: #FF5252; font-size: 12px;")
            self._progress_bar.hide()
            self._start_btn.setEnabled(True)
            self._name_input.setEnabled(True)
            self._close_btn.setEnabled(True)

    def auto_close(self) -> None:
        """自动关闭对话框"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1200, self.close)

    @property
    def cookie_saved(self) -> bool:
        return self._cookie_saved
