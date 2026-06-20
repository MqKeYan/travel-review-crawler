"""
模块名称：任务卡片组件

功能说明：
    - 在任务列表中展示单个任务的摘要信息
    - 显示任务名称、网站、状态、进度、条数
    - 支持状态颜色标识
    - 支持实时刷新状态和进度
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from src.models.task import Task, TaskStatus


class TaskCard(QFrame):
    """
    任务卡片组件。

    展示单个任务的摘要信息，可点击选中。
    根据不同状态显示不同颜色的标识。

    Signal:
        clicked(str): 卡片被点击，发送任务名称
    """

    clicked = Signal(str)

    # 状态显示配置：(显示文本, QSS 样式类名, 颜色代码)
    STATUS_CONFIG = {
        TaskStatus.PENDING: ("待开始", "statusPending", "#999999"),
        TaskStatus.RUNNING: ("进行中", "statusRunning", "#FFAB00"),
        TaskStatus.PAUSED: ("已暂停", "statusPaused", "#FFAB00"),
        TaskStatus.COMPLETED: ("已完成", "statusComplete", "#00E676"),
        TaskStatus.ERROR: ("出错", "statusError", "#FF5252"),
        TaskStatus.CANCELLED: ("已取消", "statusCancelled", "#666666"),
    }

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self._task = task
        self.setObjectName("taskCard")
        self._status_label: QLabel | None = None
        self._progress_label: QLabel | None = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """初始化卡片 UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ---- 第一行：名称 + 状态 ----
        header = QHBoxLayout()

        name_label = QLabel(self._task.task_name or "未命名任务")
        name_label.setFont(QFont("微软雅黑", 15, QFont.Weight.Bold))
        name_label.setObjectName("taskCardName")

        sc = self.STATUS_CONFIG.get(self._task.status, self.STATUS_CONFIG[TaskStatus.PENDING])
        self._status_label = QLabel(sc[0])
        self._status_label.setStyleSheet(f"color: {sc[2]}; font-weight: bold; font-size: 14px;")

        header.addWidget(name_label)
        header.addStretch()
        header.addWidget(self._status_label)
        layout.addLayout(header)

        # ---- 第二行：目标网站 + 时间 ----
        info = QHBoxLayout()

        site_label = QLabel(f"网站: {self._task.site_display_name or self._task.site}")
        site_label.setObjectName("taskMiniSite")

        time_label = QLabel(f"创建: {self._task.created_at}")
        time_label.setObjectName("taskMiniTime")

        info.addWidget(site_label)
        info.addStretch()
        info.addWidget(time_label)
        layout.addLayout(info)

        # ---- 第三行：进度信息 ----
        self._progress_label = self._build_progress_label()
        if self._progress_label:
            layout.addWidget(self._progress_label)

        self.setLayout(layout)

    def _build_progress_label(self) -> QLabel | None:
        """根据当前任务状态构建进度/结果标签"""
        p = self._task.progress
        if self._task.status == TaskStatus.RUNNING and p.total > 0:
            lbl = QLabel(f"进度: {p.current}/{p.total} ({p.percentage:.0f}%)")
            lbl.setStyleSheet("color: #E65100; font-size: 12px;")
            return lbl
        elif self._task.status == TaskStatus.COMPLETED:
            lbl = QLabel(f"共 {self._task.total_reviews} 条评论")
            lbl.setStyleSheet("color: #00A844; font-size: 12px;")
            return lbl
        elif self._task.status == TaskStatus.ERROR:
            lbl = QLabel("运行出错，详见日志")
            lbl.setStyleSheet("color: #C62828; font-size: 12px;")
            return lbl
        return None

    def refresh_display(self) -> None:
        """实时刷新状态和进度文本（不重建卡片）"""
        if self._status_label:
            sc = self.STATUS_CONFIG.get(self._task.status, self.STATUS_CONFIG[TaskStatus.PENDING])
            self._status_label.setText(sc[0])
            self._status_label.setStyleSheet(f"color: {sc[2]}; font-weight: bold; font-size: 12px;")

        if self._progress_label:
            new_lbl = self._build_progress_label()
            if new_lbl:
                self._progress_label.setText(new_lbl.text())
                self._progress_label.setStyleSheet(new_lbl.styleSheet())
                self._progress_label.show()
            else:
                self._progress_label.hide()

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件：选中卡片并发送信号"""
        super().mousePressEvent(event)
        self.clicked.emit(self._task.task_name)

    @property
    def task_name(self) -> str:
        return self._task.task_name
