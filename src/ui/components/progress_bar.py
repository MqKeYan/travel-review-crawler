"""
模块名称：爬取进度条组件

功能说明：
    - 显示爬取任务的实时进度
    - QProgressBar + 百分比 + 状态描述 + ETA
    - 支持完成/错误状态的切换
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ProgressBar(QWidget):
    """
    爬取进度条组件。

    显示当前爬取进度、速度、预计剩余时间。
    支持实时更新进度数据。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化进度条 UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- 进度条 + 实时速度（同行右对齐） ----
        bar_row = QHBoxLayout()
        bar_row.setContentsMargins(0, 0, 0, 0)
        bar_row.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFixedHeight(22)
        bar_row.addWidget(self._progress_bar, 1)

        self._speed_label = QLabel("")
        self._speed_label.setStyleSheet("color: #E65100; font-size: 15px; font-weight: bold;")
        self._speed_label.setMinimumWidth(110)
        self._speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        bar_row.addWidget(self._speed_label)

        layout.addLayout(bar_row)

        # ---- 信息行：状态消息 + ETA ----
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)

        self._message_label = QLabel("等待开始...")
        self._message_label.setObjectName("progressMessage")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._eta_label = QLabel("")
        self._eta_label.setStyleSheet("color: #E65100; font-size: 13px; font-weight: bold;")

        info_layout.addWidget(self._message_label)
        info_layout.addStretch()
        info_layout.addWidget(self._eta_label)

        layout.addLayout(info_layout)
        self.setLayout(layout)

    def update_progress(self, progress_data: dict) -> None:
        """
        更新进度显示。

        从 CrawlWorker 的 progress Signal 接收数据。

        Args:
            progress_data: 包含 current, total, percentage, message, speed, eta 的字典
        """
        percentage = progress_data.get("percentage", 0)
        message = progress_data.get("message", "")
        speed = progress_data.get("speed", "")
        eta = progress_data.get("eta", "")

        self._progress_bar.setValue(int(percentage))
        # 设置进度条文本
        current = progress_data.get("current", 0)
        total = progress_data.get("total", 0)
        if total > 0:
            self._progress_bar.setFormat(f"{current}/{total} ({percentage:.0f}%)")
        else:
            self._progress_bar.setFormat(f"{current} 条")

        self._message_label.setText(message or "爬取中...")
        self._speed_label.setText(speed if speed else "")
        self._eta_label.setText(f"预计: {eta}" if eta else "")

    def set_complete(self, count: int) -> None:
        """
        设置为完成状态。

        Args:
            count: 最终爬取条数
        """
        self._progress_bar.setValue(100)
        self._progress_bar.setFormat(f"完成 {count} 条")
        self._progress_bar.setStyleSheet("")
        self._message_label.setText("爬取完成")
        self._message_label.setStyleSheet("color: #00A844; font-size: 12px; font-weight: bold;")
        self._speed_label.setText("")
        self._eta_label.setText("")

    def set_error(self, error_info: str) -> None:
        """
        设置为错误状态。

        Args:
            error_info: 错误描述
        """
        self._message_label.setText(f"错误: {error_info}")
        self._message_label.setStyleSheet("color: #C62828; font-size: 12px;")

    def reset(self) -> None:
        """重置进度条到初始状态"""
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("")
        self._message_label.setText("等待开始...")
        self._message_label.setStyleSheet("")
        self._speed_label.setText("")
        self._eta_label.setText("")
        # 重置样式
        self._progress_bar.setStyleSheet("")
