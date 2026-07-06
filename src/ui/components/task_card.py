"""
模块名称：任务卡片组件

功能说明：
    - 在任务列表中展示单个任务的摘要信息
    - 显示任务名称、网站、状态、进度、条数
    - 支持状态颜色标识
    - 支持实时刷新状态和进度
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QPainter, QCursor

from src.models.task import Task, TaskStatus


class _ElidedLabel(QLabel):
    """自动省略过长文本的标签，超宽部分显示 "…" """

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)
        painter.end()


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
        # 悬停 1 秒后弹出任务名称提示（自定义浮动标签，不受 Qt 工具提示系统干扰）
        self._tip_label: QLabel | None = None
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(1000)
        self._hover_timer.timeout.connect(self._show_hover_tip)
        self.setMouseTracking(True)
        self.setup_ui()

    def minimumSizeHint(self):
        """宽度不受限，允许布局将卡片压缩到容器宽度以内"""
        hint = super().minimumSizeHint()
        hint.setWidth(0)
        return hint

    def setup_ui(self) -> None:
        """初始化卡片 UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ---- 第一行：名称 + 状态 ----
        header = QHBoxLayout()

        name_label = _ElidedLabel(f"任务名称：{self._task.task_name or '未命名任务'}")
        name_label.setFont(QFont("微软雅黑", 15, QFont.Weight.Bold))
        name_label.setObjectName("taskCardName")
        name_label.setMinimumWidth(0)

        sc = self.STATUS_CONFIG.get(self._task.status, self.STATUS_CONFIG[TaskStatus.PENDING])
        self._status_label = QLabel(sc[0])
        self._status_label.setStyleSheet(f"color: {sc[2]}; font-weight: bold; font-size: 14px;")
        # 状态标签固定宽度，不被长名称挤压
        self._status_label.setMinimumWidth(self._status_label.sizeHint().width())

        header.addWidget(name_label, 1)  # stretch=1，填满剩余空间
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

    def enterEvent(self, event) -> None:
        """鼠标进入卡片区域，启动 1 秒倒计时"""
        self._hover_timer.start()

    def leaveEvent(self, event) -> None:
        """鼠标离开卡片区域时取消倒计时并隐藏提示"""
        self._hover_timer.stop()
        self._hide_tip()

    def mouseMoveEvent(self, event) -> None:
        """鼠标在卡片内移动时，隐藏提示并重新计时"""
        self._hide_tip()
        self._hover_timer.start()
        super().mouseMoveEvent(event)

    def _show_hover_tip(self) -> None:
        """1 秒后弹出任务名称浮动标签，固定在鼠标停留位置的上方"""
        if self._tip_label is None:
            self._tip_label = QLabel(self.window())
            self._tip_label.setWindowFlags(Qt.WindowType.ToolTip)
            self._tip_label.setFont(QFont("微软雅黑", 13))
            self._tip_label.setStyleSheet(
                "background-color: #1f231f; color: #E8E8E8;"
                "padding: 6px 10px; border-radius: 6px;"
            )
        self._tip_label.setText(f"任务名称：{self._task.task_name}")
        self._tip_label.adjustSize()
        # 悬浮窗水平中心对齐指针，下边界对齐指针上边界
        pos = QCursor.pos()
        self._tip_label.move(pos.x() - self._tip_label.width() // 2, pos.y() - self._tip_label.height())
        self._tip_label.show()

    def _hide_tip(self) -> None:
        """隐藏浮动提示"""
        if self._tip_label:
            self._tip_label.hide()

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件：选中卡片并发送信号"""
        self._hide_tip()
        super().mousePressEvent(event)
        self.clicked.emit(self._task.task_name)

    @property
    def task_name(self) -> str:
        return self._task.task_name
