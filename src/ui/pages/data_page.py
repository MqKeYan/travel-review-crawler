"""
模块名称：数据查看/导出页面

功能说明：
    - 选择已完成的任务查看其爬取数据
    - 数据表格预览
    - 数据统计（评分分布等）
    - 导出按钮（选择格式和字段后导出）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QStackedWidget,
    QCheckBox, QGroupBox, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.ui.components.data_table import DataTable
from src.models.review import STANDARD_FIELDS, ReviewStats


class StatsCard(QFrame):
    """简易统计卡片"""

    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("taskCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(2)

        self._value_label = QLabel(value)
        self._value_label.setFont(QFont("微软雅黑", 26, QFont.Weight.Bold))
        self._value_label.setStyleSheet("color: #00873E;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(label)
        lbl.setObjectName("statCardTitle")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._value_label)
        layout.addSpacing(2)
        layout.addWidget(lbl)
        self.setLayout(layout)

    def update_stats(self, value: str) -> None:
        """更新显示的数值"""
        self._value_label.setText(value)


class DataPage(QWidget):
    """
    数据查看/导出页面。

    选择已完成的任务，预览其评论数据，并可导出。

    Signal:
        export_requested(str, list[str], list[str], bool): 导出请求（任务名，格式列表，字段列表，仅选中行）
        task_selected(str): 任务选择变化（任务名）
    """

    export_requested = Signal(str, list, list, bool)
    task_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_task: str | None = None
        self._available_tasks: list[dict] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化数据页面 UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 17, 32, 20)
        layout.setSpacing(16)

        # ---- 标题行 ----
        header = QHBoxLayout()
        title = QLabel("数据查看与导出")
        title.setFont(QFont("微软雅黑", 24, QFont.Weight.Bold))
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        selector_label = QLabel("选择任务:")
        header.addWidget(selector_label)
        self._task_selector = QComboBox()
        self._task_selector.setMinimumWidth(200)
        self._task_selector.setPlaceholderText("选择已完成的任务...")
        self._task_selector.currentIndexChanged.connect(self._on_task_changed)
        header.addWidget(self._task_selector)
        layout.addLayout(header)

        # ---- 统计卡片区（固定位置，总长度等于搜索框长度） ----
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(0)

        self._stat_total = StatsCard("总评论数", "0")
        self._stat_avg = StatsCard("平均评分", "-")
        self._stat_range = StatsCard("时间范围", "-")
        from PySide6.QtWidgets import QSizePolicy
        # 总评论数、平均评分：固定宽度 120px，位置不变
        for card in (self._stat_total, self._stat_avg):
            card.setStyleSheet("#taskCard { margin: 4px 0px; }")
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            card.setFixedWidth(120)
        # 时间范围：宽度动态填充至搜索框右边缘，文字较长时可继续向右扩展
        self._stat_range.setStyleSheet("#taskCard { margin: 4px 0px; }")
        self._stat_range.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._stat_range.setMinimumWidth(120)

        stats_layout.addWidget(self._stat_total)
        stats_layout.addSpacing(12)
        stats_layout.addWidget(self._stat_avg)
        stats_layout.addSpacing(12)
        stats_layout.addWidget(self._stat_range)
        stats_layout.addStretch()  # 匹配搜索框工具栏右侧的 stretch + 翻页控件

        layout.addLayout(stats_layout)

        # ---- 数据表格 ----
        self._data_table = DataTable()
        layout.addWidget(self._data_table, 1)

        # ---- 导出区 ----
        export_group = QGroupBox("导出数据")
        export_layout = QVBoxLayout()
        export_layout.setSpacing(8)

        # 格式行
        format_row = QHBoxLayout()
        format_row.setSpacing(12)

        self._export_xlsx_cb = QCheckBox("XLSX")
        self._export_xlsx_cb.setChecked(True)
        self._export_csv_cb = QCheckBox("CSV")
        self._export_txt_cb = QCheckBox("TXT")
        self._export_txt_cb.setChecked(False)
        self._export_docx_cb = QCheckBox("DOCX")

        self._export_btn = QPushButton("导出选中格式")
        self._export_btn.clicked.connect(self._on_export)

        format_row.addWidget(QLabel("格式:"))
        format_row.addWidget(self._export_xlsx_cb)
        format_row.addWidget(self._export_csv_cb)
        format_row.addWidget(self._export_txt_cb)
        format_row.addWidget(self._export_docx_cb)
        format_row.addStretch()
        format_row.addWidget(self._export_btn)

        export_layout.addLayout(format_row)

        # 字段选择行
        field_row = QHBoxLayout()
        field_row.setSpacing(8)
        field_row.addWidget(QLabel("导出字段:"))
        self._field_checkboxes: dict[str, QCheckBox] = {}
        for field_key, field_label in STANDARD_FIELDS:
            cb = QCheckBox(field_label)
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 11px;")
            self._field_checkboxes[field_key] = cb
            field_row.addWidget(cb)
        field_row.addStretch()
        export_layout.addLayout(field_row)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        self.setLayout(layout)

    def update_task_list(self, tasks: list[dict]) -> None:
        """
        更新可选任务列表。

        Args:
            tasks: 任务信息列表 [{"name": ..., "count": ...}, ...]
        """
        self._available_tasks = tasks
        self._task_selector.clear()
        self._task_selector.addItem("-- 请选择任务 --", "")
        for task in tasks:
            display = f"{task.get('name', '')} ({task.get('count', 0)}条)"
            self._task_selector.addItem(display, task.get("name", ""))

    def set_reviews(self, task_name: str, reviews: list[dict], stats: ReviewStats) -> None:
        """
        设置评论数据到表格。

        Args:
            task_name: 任务名称
            reviews: 评论数据列表
            stats: 统计信息
        """
        self._current_task = task_name
        self._data_table.set_reviews(reviews)

        # 更新统计卡片
        self._stat_total.update_stats(str(stats.total))
        self._stat_avg.update_stats(str(stats.avg_rating))
        date_range = f"{stats.date_range[0] or '-'} ~ {stats.date_range[1] or '-'}"
        self._stat_range.update_stats(date_range)

        # 自动取消全空字段的导出勾选
        self._auto_deselect_empty_fields(reviews)

    def _auto_deselect_empty_fields(self, reviews: list[dict]) -> None:
        """
        扫描所有评论数据，自动取消勾选全列都为空的导出字段。

        只取消勾选（不重新勾选已取消的字段），
        用户手动调整后不会被覆盖（仅在数据加载时调用一次）。
        """
        if not reviews:
            return

        # 空值判定规则：不同字段类型有不同的"空"定义
        empty_checks = {
            "rating": lambda v: v == 0 or v is None,
            "image_urls": lambda v: not v,  # 空列表
        }

        for field_key, cb in self._field_checkboxes.items():
            if not cb.isChecked():
                continue  # 已手动取消的跳过
            check = empty_checks.get(field_key, lambda v: not v)
            all_empty = all(check(r.get(field_key)) for r in reviews)
            if all_empty:
                cb.setChecked(False)

    def _on_task_changed(self, index: int) -> None:
        """任务选择变化，发出 task_selected 信号"""
        task_name = self._task_selector.currentData()
        if task_name:
            self.task_selected.emit(task_name)

    def _on_export(self) -> None:
        """导出按钮"""
        if not self._current_task:
            return

        formats = []
        if self._export_xlsx_cb.isChecked():
            formats.append("xlsx")
        if self._export_csv_cb.isChecked():
            formats.append("csv")
        if self._export_txt_cb.isChecked():
            formats.append("txt")
        if self._export_docx_cb.isChecked():
            formats.append("docx")

        if not formats:
            return

        # 选中的字段
        selected_fields = [
            k for k, cb in self._field_checkboxes.items() if cb.isChecked()
        ]

        self.export_requested.emit(
            self._current_task, formats, selected_fields, False
        )
