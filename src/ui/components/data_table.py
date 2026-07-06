"""
模块名称：数据表格组件

功能说明：
    - 使用 QTableView + QAbstractTableModel 显示评论数据
    - 支持列排序和筛选（QSortFilterProxyModel）
    - 自定义列显示
    - 分页控制
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QHeaderView,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, Signal, QEvent
from PySide6.QtGui import QFont, QColor

from src.models.review import STANDARD_FIELDS, ReviewList


class ReviewTableModel(QAbstractTableModel):
    """
    评论数据表格模型（Model/View 架构中的 Model 层）。

    将评论列表映射为二维表格，供 QTableView 渲染。
    """

    def __init__(self, reviews: ReviewList = None, parent=None):
        super().__init__(parent)
        self._reviews = reviews or []
        self._fields = [k for k, _ in STANDARD_FIELDS]
        self._headers = [v for _, v in STANDARD_FIELDS]

    def rowCount(self, parent=None) -> int:
        """返回行数（评论条数）"""
        return len(self._reviews)

    def columnCount(self, parent=None) -> int:
        """返回列数（字段数）"""
        return len(self._fields)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """返回指定单元格的数据"""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._reviews) or col >= len(self._fields):
            return None

        review = self._reviews[row]
        field = self._fields[col]
        value = review.get(field, "")

        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(value, list):
                return "; ".join(str(v) for v in value)
            return str(value) if value is not None else ""

        if role == Qt.ItemDataRole.ForegroundRole:
            # 评分列颜色（双主题通用深色变体）
            if field == "rating":
                try:
                    r = int(value)
                    if r >= 4:
                        return QColor("#00A844")
                    elif r >= 3:
                        return QColor("#E65100")
                    else:
                        return QColor("#C62828")
                except (ValueError, TypeError):
                    pass

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """返回表头"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if section < len(self._headers):
                return self._headers[section]
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return section + 1  # 行号从 1 开始
        return None

    def update_data(self, reviews: ReviewList) -> None:
        """更新全部数据"""
        self.beginResetModel()
        self._reviews = list(reviews)
        self.endResetModel()


class DataTable(QWidget):
    """
    数据表格组件，包含表格视图、搜索框和翻页控制。

    Usage:
        table = DataTable()
        table.set_reviews(review_list)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_reviews: ReviewList = []
        self._page_size = 50
        self._current_page = 1

        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化表格 UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ---- 工具栏：搜索 + 翻页 ----
        toolbar = QHBoxLayout()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索评论内容...")
        self._search_input.setFixedWidth(384)  # 与数据页三卡片总长度对齐
        self._search_input.textChanged.connect(self._on_search)

        self._page_label = QLabel("第 0 页 / 共 0 页")
        self._page_label.setObjectName("dataTablePageLabel")

        self._prev_btn = QPushButton("上一页")
        self._prev_btn.setObjectName("secondaryBtn")
        self._prev_btn.setStyleSheet("QPushButton { min-height: 0px; padding: 11px 12px; }")
        self._prev_btn.clicked.connect(self._prev_page)

        self._next_btn = QPushButton("下一页")
        self._next_btn.setObjectName("secondaryBtn")
        self._next_btn.setStyleSheet("QPushButton { min-height: 0px; padding: 11px 12px; }")
        self._next_btn.clicked.connect(self._next_page)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(0)
        self._page_spin.setMaximum(0)
        self._page_spin.setValue(0)
        self._page_spin.setFixedWidth(80)
        self._page_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._page_spin.setStyleSheet(
            "QSpinBox::up-button { width: 0px; }"
            "QSpinBox::down-button { width: 0px; }"
        )
        self._page_spin.installEventFilter(self)
        self._page_spin.valueChanged.connect(self._go_to_page)

        toolbar.addWidget(self._search_input)
        toolbar.addStretch()
        toolbar.addWidget(self._prev_btn)
        toolbar.addWidget(self._page_spin)
        toolbar.addWidget(self._page_label)
        toolbar.addWidget(self._next_btn)

        layout.addLayout(toolbar)

        # ---- 表格视图 ----
        self._model = ReviewTableModel()
        self._proxy_model = QSortFilterProxyModel()
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setFilterKeyColumn(-1)  # 搜索所有列
        self._proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self._table_view = QTableView()
        self._table_view.setModel(self._proxy_model)
        self._table_view.setSortingEnabled(True)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table_view.horizontalHeader().setStretchLastSection(True)  # 末列拉伸填满，无水平滚动条
        self._table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table_view.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(self._table_view)
        self.setLayout(layout)

    def set_reviews(self, reviews: ReviewList) -> None:
        """
        设置评论数据。

        Args:
            reviews: 标准评论对象列表
        """
        self._all_reviews = list(reviews)
        self._current_page = 1
        self._update_page()

    def _update_page(self) -> None:
        """更新当前页显示"""
        total = len(self._all_reviews)

        if total == 0:
            # 无数据时页码显示 0
            self._current_page = 0
            self._model.update_data([])
            self._page_spin.setMaximum(0)
            self._page_spin.setValue(0)
            self._page_label.setText("第 0 页 / 共 0 页（共 0 条）")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            return

        total_pages = max(1, (total + self._page_size - 1) // self._page_size)

        if self._current_page < 1:
            self._current_page = 1
        if self._current_page > total_pages:
            self._current_page = total_pages

        start = (self._current_page - 1) * self._page_size
        end = start + self._page_size
        page_data = self._all_reviews[start:end]

        self._model.update_data(page_data)
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(total_pages)
        self._page_spin.setValue(self._current_page)
        self._page_label.setText(f"第 {self._current_page} 页 / 共 {total_pages} 页（共 {total} 条）")

        # 更新翻页按钮状态
        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < total_pages)

    def get_filtered_reviews(self) -> ReviewList:
        """
        获取当前过滤后的所有评论数据（用于导出）。

        Returns:
            评论数据列表
        """
        return list(self._all_reviews)

    def get_selected_rows(self) -> ReviewList:
        """
        获取表格中选中的行对应的评论数据。

        Returns:
            选中行的评论数据列表
        """
        selection_model = self._table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            return []

        rows = set()
        for idx in selection_model.selectedRows():
            # 通过 proxy model 映射回原始 model 的行号
            source_idx = self._proxy_model.mapToSource(idx)
            rows.add(source_idx.row())

        return [self._all_reviews[r] for r in sorted(rows)]

    def _on_search(self, text: str) -> None:
        """搜索框内容变化：过滤表格"""
        self._proxy_model.setFilterFixedString(text)

    def _prev_page(self) -> None:
        """上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._update_page()

    def _next_page(self) -> None:
        """下一页"""
        total = len(self._all_reviews)
        if total == 0:
            return
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        if self._current_page < total_pages:
            self._current_page += 1
            self._update_page()

    def _go_to_page(self, page: int) -> None:
        """跳转到指定页"""
        if len(self._all_reviews) == 0:
            return
        if page > 0 and page != self._current_page:
            self._current_page = page
            self._update_page()

    def eventFilter(self, obj, event):
        """禁用页码框的鼠标滚轮"""
        if obj is self._page_spin and event.type() == QEvent.Type.Wheel:
            event.ignore()
            return True
        return super().eventFilter(obj, event)
