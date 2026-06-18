"""
模块名称：暗夜绿 QSS 主题

功能说明：
    - 提供完整的暗夜绿风格的 QSS 样式表
    - 翠绿色调、深色背景
    - 覆盖常见 PySide6 控件的样式

配色方案：
    主背景: #1a1d1a     深色底板
    侧边栏: #252825     略浅
    列表栏: #1f221f     中间色
    主色调: #00C853     翠绿色
    文字主色: #E0E0E0   浅灰白
    文字辅色: #999999   次级
    卡片背景: #2a2f2a   卡片底色
    成功: #00E676       亮绿色
    警告: #FFAB00       琥珀色
    错误: #FF5252       红色
    边框: #3a3f3a       分隔线
"""


def get_dark_forest_stylesheet() -> str:
    """
    获取暗夜绿主题的完整 QSS 样式表。

    Returns:
        适用于 setStyleSheet() 的 QSS 字符串
    """
    return """
    /* ==================== 全局样式 ==================== */
    QWidget {
        background-color: #1a1d1a;
        color: #E0E0E0;
        font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", sans-serif;
        font-size: 13px;
    }

    /* ==================== 主窗口 ==================== */
    QMainWindow {
        background-color: #1a1d1a;
    }

    /* ==================== 侧边栏 ==================== */
    #sidebar {
        background-color: #252825;
        border-right: 1px solid #3a3f3a;
        min-width: 120px;
        max-width: 160px;
    }

    #sidebar QPushButton {
        background-color: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 8px;
        padding: 10px 16px 10px 13px;
        margin: 3px 10px;
        min-height: 44px;
        font-size: 15px;
        font-weight: bold;
        color: #CCCCCC;
        text-align: center;
    }

    #sidebar QPushButton:hover {
        background-color: #2a2f2a;
        color: #FFFFFF;
        border-left: 3px solid #00C853;
        padding-left: 13px;
    }

    #sidebar QPushButton:checked,
    #sidebar QPushButton:selected {
        background-color: #00C853;
        color: #1a1d1a;
        border-left: 3px solid #00E676;
        padding-left: 13px;
    }

    #sidebar QPushButton:disabled {
        color: #00C853;
        background-color: transparent;
        font-size: 13px;
        font-weight: bold;
        border-bottom: 1px solid #3a3f3a;
        border-radius: 0;
        margin: 0 10px 8px 10px;
        padding: 8px 16px;
    }

    /* QToolTip in sidebar */
    QToolTip {
        background-color: #2a2f2a;
        color: #E0E0E0;
        border: 1px solid #3a3f3a;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
    }

    /* ==================== 列表栏 ==================== */
    #listPanel {
        background-color: #1f221f;
        border-right: 1px solid #3a3f3a;
    }

    /* ==================== 任务卡片 ==================== */
    #taskCard {
        background-color: #2a2f2a;
        border: 1px solid #3a3f3a;
        border-radius: 8px;
        padding: 12px;
        margin: 4px 8px;
    }

    #taskCard:hover {
        background-color: #303530;
        border-color: #00C853;
    }

    /* ==================== 按钮 ==================== */
    QPushButton {
        background-color: #00C853;
        color: #1a1d1a;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: bold;
        font-size: 13px;
        min-height: 32px;
    }

    QPushButton:hover {
        background-color: #00E676;
    }

    QPushButton:pressed {
        background-color: #00A844;
    }

    QPushButton:disabled {
        background-color: #3a3f3a;
        color: #666666;
    }

    /* 次要按钮（灰色） */
    QPushButton#secondaryBtn {
        background-color: #3a3f3a;
        color: #E0E0E0;
    }

    QPushButton#secondaryBtn:hover {
        background-color: #4a4f4a;
    }

    /* 危险按钮（红色） */
    QPushButton#dangerBtn {
        background-color: #FF5252;
    }

    QPushButton#dangerBtn:hover {
        background-color: #FF7362;
    }

    /* ==================== 输入框 ==================== */
    QLineEdit {
        background-color: #2a2f2a;
        color: #E0E0E0;
        border: 1px solid #3a3f3a;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }

    QLineEdit:hover {
        border-color: #4a4f4a;
    }

    QLineEdit:focus {
        border-color: #00C853;
    }

    QTextEdit, QPlainTextEdit {
        background-color: #2a2f2a;
        color: #E0E0E0;
        border: 1px solid #3a3f3a;
        border-radius: 6px;
        padding: 8px;
    }

    QTextEdit:hover, QPlainTextEdit:hover {
        border-color: #4a4f4a;
    }

    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #00C853;
    }

    /* ==================== 数字输入框 ==================== */
    QSpinBox {
        background-color: #2a2f2a;
        color: #E0E0E0;
        border: 1px solid #3a3f3a;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
        min-height: 28px;
    }

    QSpinBox:hover {
        border-color: #00C853;
    }

    QSpinBox:focus {
        border-color: #00E676;
    }

    QSpinBox::up-button, QSpinBox::down-button {
        border: none;
        background-color: #3a3f3a;
        width: 20px;
        border-radius: 3px;
        margin: 2px;
    }

    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: #00C853;
    }

    QSpinBox::up-arrow, QSpinBox::down-arrow {
        width: 8px;
        height: 8px;
    }

    /* ==================== 下拉框 ==================== */
    QComboBox {
        background-color: #2a2f2a;
        color: #E0E0E0;
        border: 1px solid #3a3f3a;
        border-radius: 6px;
        padding: 8px 12px;
        min-height: 16px;
    }

    QComboBox:hover {
        border-color: #00C853;
        background-color: #2a3f2a;
    }

    QComboBox:focus {
        border-color: #00E676;
    }

    QComboBox::drop-down {
        border: none;
        width: 30px;
        border-radius: 0px 6px 6px 0px;
    }

    QComboBox::drop-down:hover {
        background-color: #00C853;
    }

    QComboBox QAbstractItemView {
        background-color: #252825;
        color: #E0E0E0;
        border: 1px solid #00C853;
        border-radius: 4px;
        outline: none;
        padding: 2px;
    }

    QComboBox QAbstractItemView::item {
        padding: 8px 12px;
        border-radius: 4px;
        margin: 1px 2px;
    }

    QComboBox QAbstractItemView::item:hover {
        background-color: #00C853;
        color: #1a1d1a;
    }

    QComboBox QAbstractItemView::item:selected {
        background-color: #2a3f2a;
        color: #00C853;
    }

    /* ==================== 表格 ==================== */
    QTableView, QTableWidget {
        background-color: #1f221f;
        color: #E0E0E0;
        border: 1px solid #3a3f3a;
        gridline-color: #3a3f3a;
        selection-background-color: #2a3f2a;
        selection-color: #00C853;
    }

    QTableView::item, QTableWidget::item {
        padding: 8px;
        border-bottom: 1px solid #2a2f2a;
    }

    QTableView::item:hover, QTableWidget::item:hover {
        background-color: #2a2f2a;
    }

    QHeaderView::section {
        background-color: #252825;
        color: #00C853;
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid #00C853;
        font-weight: bold;
    }

    /* ==================== 进度条 ==================== */
    QProgressBar {
        background-color: #2a2f2a;
        border: 1px solid #3a3f3a;
        border-radius: 6px;
        text-align: center;
        color: #E0E0E0;
        font-size: 12px;
        min-height: 20px;
    }

    QProgressBar::chunk {
        background-color: #00C853;
        border-radius: 5px;
    }

    /* ==================== 标签 ==================== */
    QLabel {
        color: #E0E0E0;
        background-color: transparent;
    }

    QLabel#titleLabel {
        font-size: 20px;
        font-weight: bold;
        color: #00C853;
    }

    QLabel#subtitleLabel {
        font-size: 14px;
        color: #999999;
    }

    QLabel#statusComplete {
        color: #00E676;
        font-weight: bold;
    }

    QLabel#statusRunning {
        color: #FFAB00;
        font-weight: bold;
    }

    QLabel#statusError {
        color: #FF5252;
        font-weight: bold;
    }

    /* ==================== 分组框 ==================== */
    QGroupBox {
        background-color: #1f221f;
        border: 1px solid #3a3f3a;
        border-radius: 8px;
        margin-top: 16px;
        padding: 16px;
        padding-top: 24px;
        font-weight: bold;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: #00C853;
    }

    /* ==================== 滚动条 ==================== */
    QScrollBar:vertical {
        background-color: #1a1d1a;
        width: 10px;
        border: none;
    }

    QScrollBar::handle:vertical {
        background-color: #3a3f3a;
        border-radius: 5px;
        min-height: 30px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #4a4f4a;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #1a1d1a;
        height: 10px;
        border: none;
    }

    QScrollBar::handle:horizontal {
        background-color: #3a3f3a;
        border-radius: 5px;
        min-width: 30px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #4a4f4a;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ==================== 拆分器 ==================== */
    QSplitter::handle {
        background-color: #3a3f3a;
        width: 2px;
    }

    QSplitter::handle:hover {
        background-color: #00C853;
    }

    /* ==================== 对话框 ==================== */
    QDialog {
        background-color: #1a1d1a;
    }

    /* ==================== 消息框 ==================== */
    QMessageBox {
        background-color: #1a1d1a;
    }

    QMessageBox QLabel {
        color: #E0E0E0;
    }

    QMessageBox QPushButton {
        min-width: 80px;
    }

    /* ==================== 复选框 & 单选框 ==================== */
    QCheckBox {
        spacing: 8px;
        padding: 2px 0;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #3a3f3a;
        background-color: #2a2f2a;
    }

    QCheckBox::indicator:hover {
        border-color: #00C853;
        background-color: #2a3f2a;
    }

    QCheckBox::indicator:checked {
        background-color: #00C853;
        border-color: #00C853;
    }

    QCheckBox::indicator:checked:hover {
        background-color: #00E676;
        border-color: #00E676;
    }

    QCheckBox:hover {
        color: #FFFFFF;
    }

    QRadioButton {
        spacing: 8px;
        padding: 2px 0;
    }

    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid #3a3f3a;
        background-color: #2a2f2a;
    }

    QRadioButton::indicator:hover {
        border-color: #00C853;
        background-color: #2a3f2a;
    }

    QRadioButton::indicator:checked {
        background-color: #00C853;
        border-color: #00C853;
    }

    QRadioButton::indicator:checked:hover {
        background-color: #00E676;
        border-color: #00E676;
    }

    QRadioButton:hover {
        color: #FFFFFF;
    }

    /* ==================== Tab 控件 ==================== */
    QTabWidget::pane {
        background-color: #1a1d1a;
        border: 1px solid #3a3f3a;
        border-top: none;
    }

    QTabBar::tab {
        background-color: #252825;
        color: #999999;
        padding: 10px 20px;
        border: none;
        border-bottom: 2px solid transparent;
    }

    QTabBar::tab:selected {
        color: #00C853;
        border-bottom: 2px solid #00C853;
    }

    QTabBar::tab:hover {
        color: #E0E0E0;
    }

    /* ==================== 系统托盘 ==================== */
    QSystemTrayIcon {
        color: #00C853;
    }

    /* ==================== 列表视图 ==================== */
    QListView {
        background-color: #1f221f;
        border: none;
        outline: none;
    }

    QListView::item {
        padding: 8px;
        border-bottom: 1px solid #2a2f2a;
    }

    QListView::item:selected {
        background-color: #2a3f2a;
        color: #00C853;
    }

    QListView::item:hover {
        background-color: #2a2f2a;
    }
    """
