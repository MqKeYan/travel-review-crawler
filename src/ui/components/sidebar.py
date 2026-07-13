"""
模块名称：暗夜绿风格侧边栏 (Enhanced)

功能说明：
    - 左侧导航侧边栏，带图标的文字按钮
    - 五个核心页面的切换导航
    - 当前选中页面高亮显示

页面按钮映射：
    0: 首页
    1: 任务管理
    2: 数据查看
    3: 系统设置
    4: 系统记录
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor


class Sidebar(QWidget):
    """
    暗夜绿风格侧边栏 — 图标+文字导航。

    Signal:
        page_changed(int): 页面切换信号，参数为页面索引 (0~4)
    """

    page_changed = Signal(int)

    # 页面按钮配置：(显示文字, 标识)
    PAGE_BUTTONS = [
        ("首页", "首页"),
        ("任务管理", "任务"),
        ("数据查看", "数据"),
        ("系统记录", "记录"),
        ("系统设置", "设置"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化侧边栏 UI：图标+文字的垂直按钮"""
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 10, 4, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 按钮组：保证单选效果
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._buttons: list[QPushButton] = []

        for idx, (text, _) in enumerate(self.PAGE_BUTTONS):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(44)
            btn.setFont(QFont("微软雅黑", 14))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setToolTip(text)

            self._button_group.addButton(btn, idx)
            self._buttons.append(btn)
            layout.addWidget(btn)

        # 弹性占位（让按钮组靠上对齐）
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(layout)

        # 默认选中首页
        first_btn = self._button_group.button(0)
        if first_btn:
            first_btn.setChecked(True)

        # 连接信号：用每个按钮的 clicked 信号（非 idClicked）
        # clicked 在重复点击已选中按钮时也会触发，确保点击"任务管理"能清空详情
        for idx, btn in enumerate(self._buttons):
            btn.clicked.connect(lambda checked, i=idx: self.page_changed.emit(i))

    def _on_button_clicked(self, button_id: int) -> None:
        """
        按钮点击处理：发送页面切换信号。

        Args:
            button_id: 页面索引 (0~3)
        """
        self.page_changed.emit(button_id)

    def set_active(self, index: int) -> None:
        """
        设置当前激活的页面按钮（由外部调用，响应页面切换）。

        Args:
            index: 页面索引 (0~3)
        """
        btn = self._button_group.button(index)
        if btn:
            btn.setChecked(True)
