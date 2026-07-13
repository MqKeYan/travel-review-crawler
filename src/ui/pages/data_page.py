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
from src.models.review import STANDARD_FIELDS, CRAWL_TYPE_FIELDS, ReviewStats


class StatsCard(QFrame):
    """简易统计卡片（紧凑高度，正文统一字号）"""

    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("taskCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet("color: #00873E;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(label)
        lbl.setObjectName("statCardTitle")
        lbl.setStyleSheet("font-size: 15px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._value_label)
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
        self._current_crawl_type: str | None = None
        self._available_tasks: list[dict] = []
        # 任务名 → 爬取类型映射
        self._task_crawl_types: dict[str, str] = {}

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

        # ---- 数据内容区 ----
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # 统计卡片区
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(0)

        self._stat_total = StatsCard("总评论数", "0")
        self._stat_avg = StatsCard("平均评分", "-")
        self._stat_range = StatsCard("时间范围", "-")
        from PySide6.QtWidgets import QSizePolicy
        for card in (self._stat_total, self._stat_avg):
            card.setStyleSheet("#taskCard { margin: 4px 0px; }")
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            card.setFixedWidth(120)
        self._stat_range.setStyleSheet("#taskCard { margin: 4px 0px; }")
        self._stat_range.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._stat_range.setMinimumWidth(120)

        stats_layout.addWidget(self._stat_total)
        stats_layout.addSpacing(12)
        stats_layout.addWidget(self._stat_avg)
        stats_layout.addSpacing(12)
        stats_layout.addWidget(self._stat_range)
        stats_layout.addStretch()
        content_layout.addLayout(stats_layout)

        # 数据表格
        self._data_table = DataTable()
        content_layout.addWidget(self._data_table, 1)

        # 导出区
        export_group = QGroupBox("导出数据")
        export_group.setStyleSheet(
            "QGroupBox { padding: 8px; padding-top: 20px; }"
        )
        export_layout = QVBoxLayout()
        export_layout.setSpacing(2)

        # 格式行 + 导出按钮
        format_row = QHBoxLayout()
        format_row.setSpacing(8)

        self._export_xlsx_cb = QCheckBox("XLSX")
        self._export_csv_cb = QCheckBox("CSV")
        self._export_txt_cb = QCheckBox("TXT")
        self._export_docx_cb = QCheckBox("DOCX")

        self._export_btn = QPushButton("导出选中格式")
        self._export_btn.setStyleSheet(
            "min-height: 24px; padding: 6px 16px; font-size: 14px;"
        )
        self._export_btn.clicked.connect(self._on_export)

        format_row.addWidget(QLabel("格式:"))
        format_row.addWidget(self._export_xlsx_cb)
        format_row.addWidget(self._export_csv_cb)
        format_row.addWidget(self._export_txt_cb)
        format_row.addWidget(self._export_docx_cb)
        format_row.addStretch()
        format_row.addWidget(self._export_btn)
        export_layout.addLayout(format_row)

        # 导出字段（一行，紧凑排列，初始隐藏）
        self._field_row = QHBoxLayout()
        self._field_row.setSpacing(6)
        self._field_label = QLabel("导出字段:")
        self._field_row.addWidget(self._field_label)

        self._field_checkboxes: dict[str, QCheckBox] = {}
        for field_key, field_label in STANDARD_FIELDS:
            cb = QCheckBox(field_label)
            cb.setFont(QFont("微软雅黑", 11))
            self._field_checkboxes[field_key] = cb
            self._field_row.addWidget(cb)
        self._field_row.addStretch()
        export_layout.addLayout(self._field_row)

        # 初始隐藏所有字段勾选框
        self._set_field_row_visible(False)

        export_group.setLayout(export_layout)
        content_layout.addWidget(export_group)

        layout.addLayout(content_layout, 1)

        self.setLayout(layout)

    def update_task_list(self, tasks: list[dict]) -> None:
        """
        更新可选任务列表。

        Args:
            tasks: 任务信息列表 [{"name": ..., "count": ..., "crawl_type": ...}, ...]
        """
        self._available_tasks = tasks
        # 缓存任务名 → 爬取类型映射
        self._task_crawl_types = {t["name"]: t.get("crawl_type", "") for t in tasks}
        # 阻塞信号，避免 clear/addItem 过程中触发 task_selected 加载数据
        self._task_selector.blockSignals(True)
        self._task_selector.clear()
        for task in tasks:
            display = f"{task.get('name', '')} ({task.get('count', 0)}条)"
            self._task_selector.addItem(display, task.get("name", ""))
        # 折叠状态显示 placeholder 提示词
        self._task_selector.setCurrentIndex(-1)
        self._task_selector.blockSignals(False)
        # 手动触发一次清理：清空表格和统计卡片
        self._clear_table()

    def set_reviews(self, task_name: str, reviews: list[dict], stats: ReviewStats) -> None:
        """
        设置评论数据到表格。

        Args:
            task_name: 任务名称
            reviews: 评论数据列表
            stats: 统计信息
        """
        self._current_task = task_name
        self._current_crawl_type = self._task_crawl_types.get(task_name, "")

        # 按爬取类型确定显示字段
        type_fields = CRAWL_TYPE_FIELDS.get(self._current_crawl_type)
        self._data_table.set_reviews(reviews, fields=type_fields)

        # 更新统计卡片
        self._stat_total.update_stats(str(stats.total))
        self._stat_avg.update_stats(str(stats.avg_rating))
        date_range = f"{stats.date_range[0] or '-'} ~ {stats.date_range[1] or '-'}"
        self._stat_range.update_stats(date_range)

        # 根据爬取类型显示/隐藏导出字段
        self._update_fields_by_type()

        # 自动取消勾选全列为空的字段
        self._auto_uncheck_empty_columns(reviews)

        # 按用户设置的默认导出格式勾选
        from src.services.system_service import SystemService
        default_fmt = SystemService().get_setting("export.default_format", "xlsx")
        self._export_xlsx_cb.setChecked(default_fmt == "xlsx")
        self._export_csv_cb.setChecked(default_fmt == "csv")
        self._export_txt_cb.setChecked(default_fmt == "txt")
        self._export_docx_cb.setChecked(default_fmt == "docx")

    def _update_fields_by_type(self) -> None:
        """
        根据当前任务的爬取类型控制导出字段的显隐：
        - 无类型时隐藏整个字段行
        - 有类型时仅显示该类型定义的字段，全勾选
        """
        if not self._current_crawl_type:
            self._set_field_row_visible(False)
            return

        type_fields = CRAWL_TYPE_FIELDS.get(self._current_crawl_type, [])
        if not type_fields:
            self._set_field_row_visible(False)
            return

        for field_key, cb in self._field_checkboxes.items():
            if field_key in type_fields:
                cb.setVisible(True)
                cb.setChecked(True)
            else:
                cb.setVisible(False)
                cb.setChecked(False)  # 隐藏的字段取消勾选，防止被意外导出

        # 只显示"导出字段:"标签，不用 _set_field_row_visible（它会覆盖 checkbox 的显隐状态）
        self._field_label.setVisible(True)

    def _auto_uncheck_empty_columns(self, reviews: list[dict]) -> None:
        """扫描数据，自动取消勾选全列为空/零值的字段。"""
        type_fields = CRAWL_TYPE_FIELDS.get(self._current_crawl_type, [])
        if not type_fields or not reviews:
            return

        for field_key in type_fields:
            cb = self._field_checkboxes.get(field_key)
            if cb is None or not cb.isVisible():
                continue
            # 检查该字段是否全部为空
            all_empty = True
            for r in reviews:
                val = r.get(field_key)
                # 空值判定：None、空字符串、空列表、0（评分）
                if val is None:
                    continue
                if isinstance(val, str) and val.strip() == "":
                    continue
                if isinstance(val, list) and len(val) == 0:
                    continue
                if isinstance(val, (int, float)) and val == 0:
                    continue
                all_empty = False
                break
            if all_empty:
                cb.setChecked(False)

    def _set_field_row_visible(self, visible: bool) -> None:
        """切换导出字段整行的可见性"""
        for i in range(self._field_row.count()):
            item = self._field_row.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(visible)

    def _clear_table(self) -> None:
        """清空表格数据、统计卡片和导出字段（回到无任务选中状态）"""
        self._current_task = None
        self._current_crawl_type = None
        self._data_table.set_reviews([])
        self._stat_total.update_stats("0")
        self._stat_avg.update_stats("-")
        self._stat_range.update_stats("-")
        # 清空导出格式勾选
        self._export_xlsx_cb.setChecked(False)
        self._export_csv_cb.setChecked(False)
        self._export_txt_cb.setChecked(False)
        self._export_docx_cb.setChecked(False)

        self._set_field_row_visible(False)

    def _on_task_changed(self, index: int) -> None:
        """任务选择变化，发出 task_selected 信号"""
        task_name = self._task_selector.currentData()
        if task_name:
            self.task_selected.emit(task_name)
        else:
            # 回到空选择状态，清空表格和导出字段
            self._clear_table()

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
