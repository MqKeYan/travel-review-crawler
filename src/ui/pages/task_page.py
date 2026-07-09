"""
模块名称：任务管理页面

功能说明：
    - 任务列表（左栏）：展示所有任务的卡片列表
    - 任务详情/操作（右区）：选中任务后显示详细信息和操作按钮
    - 支持新建任务入口

布局：
    ┌───────────────────────────┐
    │  任务列表 (左)  │ 详情/操作 (右) │
    │  任务卡片列表   │ 选中后展示详情  │
    │                │ + 进度展示      │
    │  新建任务按钮   │ + 操作按钮      │
    └───────────────────────────┘
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.models.task import Task, TaskStatus
from src.ui.components.task_card import TaskCard
from src.ui.components.progress_bar import ProgressBar


class _TaskListContainer(QWidget):
    """任务列表容器，点击空白区域发出信号清空详情"""
    empty_clicked = Signal()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        # 只在点击空白区域（非子控件）时触发
        child = self.childAt(event.position().toPoint())
        if child is None or child is self:
            self.empty_clicked.emit()

# 中文状态映射
STATUS_CN = {
    TaskStatus.PENDING: "待开始",
    TaskStatus.RUNNING: "运行中",
    TaskStatus.PAUSED: "已暂停",
    TaskStatus.COMPLETED: "已完成",
    TaskStatus.ERROR: "出错",
    TaskStatus.CANCELLED: "已取消",
}


class TaskPage(QWidget):
    """
    任务管理页面。

    Signal:
        navigate(int, dict): 导航信号，带额外参数
        create_task(): 创建新任务
        task_selected(str): 选中某任务
    """

    create_task_requested = Signal()
    task_selected = Signal(str)
    task_start_requested = Signal(str)
    task_pause_requested = Signal(str)
    task_stop_requested = Signal(str)
    task_delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: dict[str, Task] = {}
        self._selected_task_name: str | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化任务页面 UI：左右两栏布局"""
        layout = QHBoxLayout()
        layout.setContentsMargins(32, 23, 32, 20)
        layout.setSpacing(4)

        # ========== 左栏：任务列表 ==========
        left_panel = QWidget()
        left_panel.setObjectName("listPanel")
        left_panel.setMinimumWidth(320)
        left_panel.setMaximumWidth(520)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 8)
        left_layout.setSpacing(8)

        # 标题
        title = QLabel("任务列表")
        title.setFont(QFont("微软雅黑", 20, QFont.Weight.Bold))
        title.setObjectName("pageTitle")
        left_layout.addWidget(title)

        # 新建任务按钮
        new_btn = QPushButton("新建爬取任务")
        new_btn.clicked.connect(self.create_task_requested.emit)
        left_layout.addWidget(new_btn)

        # 任务卡片列表（使用 QScrollArea + 垂直布局）
        self._task_scroll = QScrollArea()
        self._task_scroll.setWidgetResizable(True)
        self._task_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._task_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._task_list_widget = _TaskListContainer()
        self._task_list_widget.setMinimumWidth(0)  # 允许收缩，不撑破滚动区域
        self._task_list_widget.empty_clicked.connect(self.clear_detail)
        self._task_list_layout = QVBoxLayout()
        self._task_list_layout.setContentsMargins(0, 0, 0, 0)
        self._task_list_layout.setSpacing(4)
        self._task_list_layout.addStretch()
        self._task_list_widget.setLayout(self._task_list_layout)
        self._task_scroll.setWidget(self._task_list_widget)

        left_layout.addWidget(self._task_scroll)

        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel)

        # ========== 右栏：任务详情/操作 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 16)
        right_layout.setSpacing(12)

        # 使用 QStackedWidget 切换"空状态"和"详情"
        self._stack = QStackedWidget()

        # 空状态页面
        self._empty_page = QWidget()
        self._stack.addWidget(self._empty_page)

        # 详情页面
        self._detail_page = QWidget()
        detail_layout = QVBoxLayout()
        detail_layout.setSpacing(12)

        # 基本信息
        self._detail_info = QLabel("")
        self._detail_info.setObjectName("taskDetailInfo")
        self._detail_info.setWordWrap(True)
        detail_layout.addWidget(self._detail_info)

        # 进度条
        self._detail_progress = ProgressBar()
        detail_layout.addWidget(self._detail_progress)

        # 操作按钮
        btn_layout = QHBoxLayout()

        self._start_btn = QPushButton("开始")
        self._start_btn.clicked.connect(self._on_start)

        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setObjectName("secondaryBtn")
        self._pause_btn.clicked.connect(self._on_pause)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.setObjectName("dangerBtn")
        self._stop_btn.clicked.connect(self._on_stop)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setObjectName("secondaryBtn")
        self._delete_btn.clicked.connect(self._on_delete)

        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._pause_btn)
        btn_layout.addWidget(self._stop_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._delete_btn)

        detail_layout.addLayout(btn_layout)
        detail_layout.addStretch()
        self._detail_page.setLayout(detail_layout)
        self._stack.addWidget(self._detail_page)

        right_layout.addWidget(self._stack)
        right_panel.setLayout(right_layout)
        layout.addWidget(right_panel, 1)  # stretch=1

        self.setLayout(layout)
        self._stack.setCurrentIndex(0)  # 默认显示空状态

    def set_tasks(self, tasks: list[Task]) -> None:
        """
        更新任务列表显示。

        每个任务使用 TaskCard 卡片展示在滚动列表中，
        移除旧卡片并重新构建列表。

        Args:
            tasks: 任务对象列表
        """
        # 清空旧卡片（保留最后一个 stretch 项）
        while self._task_list_layout.count() > 1:
            item = self._task_list_layout.takeAt(0)
            if item and item.widget():
                w = item.widget()
                w.hide()         # 立即隐藏，防止拦截新卡片鼠标事件
                w.deleteLater()

        self._tasks.clear()

        for task in tasks:
            self._tasks[task.task_name] = task
            card = TaskCard(task)
            card.clicked.connect(self._on_card_clicked)
            self._task_list_layout.insertWidget(
                self._task_list_layout.count() - 1, card
            )

    def _on_card_clicked(self, task_name: str) -> None:
        """卡片被点击"""
        self._show_detail(task_name)

    def clear_detail(self) -> None:
        """清空详情面板，回到空状态"""
        self._selected_task_name = None
        self._stack.setCurrentIndex(0)

    def _show_detail(self, task_name: str) -> None:
        """显示任务详情"""
        task = self._tasks.get(task_name)
        if not task:
            return

        self._selected_task_name = task_name
        self._stack.setCurrentIndex(1)
        # 强制从空页面(0高度)切换到详情页后重新计算布局
        self._stack.updateGeometry()
        self.layout().activate()

        status_text = STATUS_CN.get(task.status, task.status.value if task.status else "未知")
        self._detail_info.setText(
            f"任务名称：{task.task_name}\n"
            f"网站: {task.site_display_name or task.site}\n"
            f"目标 URL: {task.target_url}\n"
            f"状态: {status_text}\n"
            f"创建时间: {task.created_at}\n"
            f"评论数: {task.total_reviews}"
        )

        # 更新操作按钮状态
        if task.status == TaskStatus.RUNNING:
            self._start_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        elif task.status == TaskStatus.PAUSED:
            self._start_btn.setEnabled(True)
            self._start_btn.setText("恢复")
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
        else:
            self._start_btn.setEnabled(True)
            self._start_btn.setText("开始")
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

        # 同步进度条：根据选中任务的实际状态回显/重置进度
        if task.status == TaskStatus.COMPLETED:
            self._detail_progress.set_complete(task.total_reviews)
        elif task.status == TaskStatus.RUNNING:
            p = task.progress
            self._detail_progress.update_progress({
                "current": p.current, "total": p.total,
                "percentage": p.percentage, "current_page": p.current_page,
                "message": p.message, "speed": p.speed, "eta": p.eta,
            })
        elif task.status == TaskStatus.ERROR:
            self._detail_progress.set_error("任务出错")
        else:
            self._detail_progress.reset()

        self.task_selected.emit(task_name)

    def refresh_detail(self) -> None:
        """刷新当前选中任务的详情（按钮状态等）"""
        if self._selected_task_name:
            self._show_detail(self._selected_task_name)

    def update_detail_progress(self, task_name: str, progress_data: dict) -> None:
        """实时更新详情页的进度条（仅当进度属于当前选中任务时更新）"""
        if self._stack.currentIndex() == 1 and self._selected_task_name == task_name:
            self._detail_progress.update_progress(progress_data)

    def refresh_task_card(self, task_name: str) -> None:
        """实时刷新指定任务的卡片显示"""
        for i in range(self._task_list_layout.count()):
            item = self._task_list_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, TaskCard) and card.task_name == task_name:
                    card.refresh_display()
                    break

    def _on_start(self) -> None:
        """开始/恢复按钮"""
        if self._selected_task_name:
            self.task_start_requested.emit(self._selected_task_name)

    def _on_pause(self) -> None:
        """暂停按钮"""
        if self._selected_task_name:
            self.task_pause_requested.emit(self._selected_task_name)

    def _on_stop(self) -> None:
        """停止按钮"""
        if self._selected_task_name:
            self.task_stop_requested.emit(self._selected_task_name)

    def _on_delete(self) -> None:
        """删除按钮"""
        if self._selected_task_name:
            self.task_delete_requested.emit(self._selected_task_name)
