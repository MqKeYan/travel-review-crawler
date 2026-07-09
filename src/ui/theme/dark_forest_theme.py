"""
模块名称：暗夜绿 / 晨曦绿 双主题 QSS

功能说明：
    - 提供暗夜绿（dark）和晨曦绿（light）两套完整的 QSS 样式表
    - 翠绿色调统一贯穿两个主题
    - 覆盖常见 PySide6 控件的样式

配色方案 (暗色):
    主背景: #0f120f    底板
    主色调: #00C853    翠绿色
    文字主色: #E8E8E8

配色方案 (亮色):
    主背景: #f5f7f5    底板
    主色调: #00A844    翠绿色(深一档保证对比度)
    文字主色: #1a1d1a
"""


def get_dark_forest_stylesheet() -> str:
    """
    获取暗夜绿主题的完整 QSS 样式表 (Enhanced)。

    Returns:
        适用于 setStyleSheet() 的 QSS 字符串
    """
    return """
    /* ==================== 全局样式 ==================== */
    QWidget {
        background-color: #0f120f;
        color: #E8E8E8;
        font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", sans-serif;
        font-size: 15px;
    }

    /* ==================== 主窗口 ==================== */
    QMainWindow {
        background-color: #0f120f;
    }

    /* ==================== 侧边栏 ==================== */
    #sidebar {
        background-color: #121412;
        border-right: 1px solid #1e221e;
        min-width: 130px;
        max-width: 180px;
    }

    #sidebar QPushButton {
        background-color: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 8px;
        padding: 10px 10px 8px 10px;
        margin: 3px 6px;
        min-height: 42px;
        font-size: 14px;
        font-weight: bold;
        color: #B0B0B0;
        text-align: center;
    }

    #sidebar QPushButton:hover {
        background-color: #1f251f;
        color: #FFFFFF;
        border-left: 3px solid #00C853;
    }

    #sidebar QPushButton:checked,
    #sidebar QPushButton:selected {
        background-color: #00C853;
        color: #0f120f;
        border-left: 3px solid #00E676;
        font-weight: bold;
    }

    #sidebar QPushButton:disabled {
        color: #00C853;
        background-color: transparent;
        font-size: 13px;
        font-weight: bold;
        border-bottom: 1px solid #2a2f2a;
        border-radius: 0;
        margin: 4px 8px 12px 8px;
        padding: 10px 10px 6px 10px;
    }

    /* ==================== 列表栏 ==================== */
    /* ==================== 卡片 ==================== */
    #taskCard {
        background-color: #1f231f;
        border: 1px solid #2a2f2a;
        border-radius: 10px;
        padding: 14px;
        margin: 4px 8px;
    }

    #taskCard:hover {
        background-color: #252a25;
        border-color: #00C853;
    }

    /* ==================== 系统信息栏 ==================== */
    #systemInfoBar {
        background-color: #1a1e1a;
        border-radius: 8px;
        border: 1px solid #252a25;
    }

    #sysInfoItem {
        color: #B0B0B0;
        font-size: 14px;
    }

    #sysInfoItemOk {
        color: #00C853;
        font-size: 14px;
    }

    #sysInfoItemErr {
        color: #FF5252;
        font-size: 14px;
    }

    #sysInfoSep {
        color: #2a2f2a;
        font-size: 16px;
        padding: 0 4px;
    }

    /* ==================== 统计卡片 ==================== */
    #statCardTitle {
        color: #9E9E9E;
        font-size: 14px;
    }

    #statCardValue {
        font-size: 30px;
        font-weight: bold;
    }

    /* ==================== 任务迷你卡片 ==================== */
    #taskMiniName {
        color: #E8E8E8;
        font-size: 14px;
        font-weight: bold;
    }

    #taskMiniSite {
        color: #9E9E9E;
        font-size: 14px;
    }

    #taskMiniCount {
        color: #448AFF;
        font-size: 14px;
        font-weight: bold;
    }

    #taskMiniTime {
        color: #7a7a7a;
        font-size: 13px;
    }

    /* ==================== 首页区域 ==================== */
    #homeSectionTitle {
        color: #E8E8E8;
        font-size: 18px;
        font-weight: bold;
        padding-top: 12px;
        padding-bottom: 4px;
    }

    #homeTableHeader {
        color: #7a7a7a;
        font-size: 13px;
    }

    #homeNoData {
        color: #666666;
        font-size: 14px;
        padding: 24px;
    }

    /* ==================== 按钮 ==================== */
    QPushButton {
        background-color: #00C853;
        color: #0f120f;
        border: none;
        border-radius: 7px;
        padding: 9px 24px;
        font-weight: bold;
        font-size: 15px;
        min-height: 36px;
    }

    QPushButton:hover {
        background-color: #00E676;
    }

    QPushButton:pressed {
        background-color: #009c3f;
    }

    QPushButton:disabled {
        background-color: #252a25;
        color: #5a5a5a;
    }

    /* 次要按钮 */
    QPushButton#secondaryBtn {
        background-color: #252a25;
        color: #CCCCCC;
        border: 1px solid #3a3f3a;
    }

    QPushButton#secondaryBtn:hover {
        background-color: #303530;
        border-color: #00C853;
        color: #FFFFFF;
    }

    QPushButton#secondaryBtn:pressed {
        background-color: #1f231f;
    }

    QPushButton#secondaryBtn:disabled {
        background-color: #1a1d1a;
        color: #5a5a5a;
        border-color: #2a2f2a;
    }

    /* 危险按钮 */
    QPushButton#dangerBtn {
        background-color: #FF5252;
        color: #FFFFFF;
    }

    QPushButton#dangerBtn:hover {
        background-color: #FF7362;
    }

    QPushButton#dangerBtn:pressed {
        background-color: #D32F2F;
    }

    QPushButton#dangerBtn:disabled {
        background-color: #4a2020;
        color: #8a5a5a;
    }

    /* ==================== 输入框 ==================== */
    QLineEdit {
        background-color: #1f231f;
        color: #E8E8E8;
        border: 1px solid #2a2f2a;
        border-radius: 7px;
        padding: 10px 14px;
        font-size: 15px;
    }

    QLineEdit:hover {
        border-color: #3a3f3a;
    }

    QLineEdit:focus {
        border-color: #00C853;
        background-color: #1a221a;
    }

    QTextEdit, QPlainTextEdit {
        background-color: #1f231f;
        color: #E8E8E8;
        border: 1px solid #2a2f2a;
        border-radius: 7px;
        padding: 10px;
    }

    QTextEdit:hover, QPlainTextEdit:hover {
        border-color: #3a3f3a;
    }

    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #2a2f2a;
    }

    /* 日志显示区域 — 左上直角 */
    #logTextEdit {
        padding: 4px;
        border-top-left-radius: 0px;
    }

    /* 日志标签页容器 — 无背景框格 */
    #logTabWidget::pane {
        background-color: transparent;
        border: none;
    }

    /* 日志标签页 — 首尾按钮加圆角 */
    #logTabWidget QTabBar::tab:first {
        border-top-left-radius: 8px;
    }
    #logTabWidget QTabBar::tab:last {
        border-top-right-radius: 8px;
    }

    /* ==================== 数字输入框 ==================== */
    QSpinBox {
        background-color: #1f231f;
        color: #E8E8E8;
        border: 1px solid #2a2f2a;
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 14px;
        min-height: 30px;
    }

    QSpinBox:hover {
        border-color: #00C853;
    }

    QSpinBox:focus {
        border-color: #00E676;
    }

    QSpinBox::up-button, QSpinBox::down-button {
        border: none;
        background-color: #2a2f2a;
        width: 22px;
        border-radius: 3px;
        margin: 3px;
    }

    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: #00C853;
    }

    /* ==================== 下拉框 ==================== */
    QComboBox {
        background-color: #1f231f;
        color: #E8E8E8;
        border: 1px solid #2a2f2a;
        border-radius: 7px;
        padding: 10px 14px;
        min-height: 18px;
    }

    QComboBox:hover {
        border-color: #00C853;
    }

    QComboBox:focus {
        border-color: #00E676;
    }

    QComboBox::drop-down {
        border: none;
        width: 30px;
        border-radius: 0px 7px 7px 0px;
    }

    QComboBox::drop-down:hover {
        background-color: #00C853;
    }

    QComboBox QAbstractItemView {
        background-color: #1a1d1a;
        color: #E8E8E8;
        border: 1px solid #00C853;
        border-radius: 6px;
        outline: none;
        padding: 4px;
    }

    QComboBox QAbstractItemView::item {
        padding: 10px 14px;
        border-radius: 6px;
        margin: 1px 2px;
    }

    QComboBox QAbstractItemView::item:hover {
        background-color: #00C853;
        color: #0f120f;
    }

    QComboBox QAbstractItemView::item:selected {
        background-color: #1a301a;
        color: #00C853;
    }

    /* ==================== 表格 ==================== */
    QTableView, QTableWidget {
        background-color: #161916;
        color: #E8E8E8;
        border: 1px solid #2a2f2a;
        border-radius: 8px;
        gridline-color: #1e221e;
        selection-background-color: #1a301a;
        selection-color: #00E676;
    }

    QTableView::item, QTableWidget::item {
        padding: 9px;
        border-bottom: 1px solid #1a1d1a;
    }

    QTableView::item:hover, QTableWidget::item:hover {
        background-color: #1f251f;
    }

    QTableView::item:alternate, QTableWidget::item:alternate {
        background-color: #181b18;
    }

    QHeaderView::section {
        background-color: #1a1e1a;
        color: #00C853;
        padding: 12px 10px;
        border: none;
        border-bottom: 2px solid #00C853;
        font-weight: bold;
        font-size: 14px;
    }

    /* ==================== 进度条 ==================== */
    QProgressBar {
        background-color: #1f231f;
        border: 1px solid #2a2f2a;
        border-radius: 8px;
        text-align: center;
        color: #E8E8E8;
        font-size: 13px;
        font-weight: bold;
        min-height: 24px;
    }

    QProgressBar::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #009c3f, stop:0.5 #00C853, stop:1 #00E676);
        border-radius: 6px;
    }

    /* ==================== 标签 ==================== */
    QLabel {
        color: #E8E8E8;
        background-color: transparent;
    }

    QLabel#titleLabel {
        font-size: 24px;
        font-weight: bold;
        color: #00C853;
    }

    QLabel#subtitleLabel {
        font-size: 15px;
        color: #9E9E9E;
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
        background-color: #161916;
        border: 1px solid #252a25;
        border-radius: 10px;
        margin-top: 18px;
        padding: 18px;
        padding-top: 28px;
        font-weight: bold;
        font-size: 15px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 6px 14px;
        color: #00C853;
        font-size: 14px;
    }

    /* ==================== 滚动条 ==================== */
    QScrollBar:vertical {
        background-color: #0f120f;
        width: 12px;
        border: none;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #2a2f2a;
        border-radius: 6px;
        min-height: 36px;
        margin: 2px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #3a3f3a;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #0f120f;
        height: 12px;
        border: none;
    }

    QScrollBar::handle:horizontal {
        background-color: #2a2f2a;
        border-radius: 6px;
        min-width: 36px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #3a3f3a;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ==================== 拆分器 ==================== */
    QSplitter::handle {
        background-color: #1e221e;
        width: 3px;
    }

    QSplitter::handle:hover {
        background-color: #00C853;
    }

    /* ==================== 对话框 ==================== */
    QDialog {
        background-color: #121412;
    }

    /* ==================== 页面通用 ==================== */
    #pageTitle {
        color: #00C853;
        font-size: 24px;
        font-weight: bold;
    }

    #dataTablePageLabel {
        color: #888888;
        font-size: 12px;
    }

    #settingsStatusHint {
        color: #888888;
        font-size: 12px;
    }

    #taskDetailInfo {
        color: #B0B0B0;
        font-size: 14px;
        line-height: 1.6;
    }

    #progressMessage {
        color: #9E9E9E;
        font-size: 13px;
    }

    #dialogTitle {
        color: #00C853;
        font-size: 18px;
        font-weight: bold;
    }

    #dialogDesc {
        color: #B0B0B0;
        font-size: 13px;
    }

    #dialogLabel {
        color: #E8E8E8;
        font-size: 14px;
    }

    #dialogHighlight {
        color: #00C853;
        font-size: 14px;
        font-weight: bold;
    }

    #dialogStatus {
        color: #888888;
        font-size: 12px;
    }

    /* ==================== 消息框 ==================== */
    QMessageBox {
        background-color: #121412;
    }

    QMessageBox QLabel {
        color: #E8E8E8;
        font-size: 14px;
    }

    QMessageBox QPushButton {
        min-width: 90px;
        min-height: 34px;
    }

    /* ==================== 复选框 ==================== */
    QCheckBox {
        spacing: 10px;
        padding: 3px 0;
        font-size: 15px;
        background-color: transparent;
    }

    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid #2a2f2a;
        background-color: #1f231f;
    }

    QCheckBox::indicator:hover {
        border-color: #00C853;
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

    /* ==================== 单选框 ==================== */
    QRadioButton {
        spacing: 10px;
        padding: 3px 0;
        font-size: 15px;
    }

    QRadioButton::indicator {
        width: 20px;
        height: 20px;
        border-radius: 10px;
        border: 2px solid #2a2f2a;
        background-color: #1f231f;
    }

    QRadioButton::indicator:hover {
        border-color: #00C853;
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
        background-color: #0f120f;
        border: 1px solid #252a25;
        border-top: none;
        border-radius: 0px 0px 8px 8px;
    }

    QTabBar::tab {
        background-color: #161916;
        color: #9E9E9E;
        padding: 12px 22px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 15px;
    }

    QTabBar::tab:selected {
        color: #00C853;
        border-bottom: 2px solid #00C853;
    }

    QTabBar::tab:hover {
        color: #E8E8E8;
        background-color: #1f231f;
    }

    /* ==================== 列表视图 ==================== */
    QListView {
        background-color: #161916;
        border: none;
        outline: none;
    }

    QListView::item {
        padding: 10px;
        border-bottom: 1px solid #1a1d1a;
    }

    QListView::item:selected {
        background-color: #1a301a;
        color: #00C853;
        border-radius: 6px;
    }

    QListView::item:hover {
        background-color: #1f231f;
        border-radius: 6px;
    }

    /* ==================== 提示框 ==================== */
    QToolTip {
        background-color: #1f231f;
        color: #E8E8E8;
        border: none;
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 13px;
    }
    """


def get_light_stylesheet() -> str:
    """
    获取晨曦绿主题的完整 QSS 样式表 (Light)。

    Returns:
        适用于 setStyleSheet() 的 QSS 字符串
    """
    return """
    /* ==================== 全局样式 ==================== */
    QWidget {
        background-color: #f5f7f5;
        color: #1a1d1a;
        font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", sans-serif;
        font-size: 14px;
    }

    /* ==================== 主窗口 ==================== */
    QMainWindow {
        background-color: #f5f7f5;
    }

    /* ==================== 侧边栏 ==================== */
    #sidebar {
        background-color: #ebedeb;
        border-right: 1px solid #d5d9d5;
        min-width: 130px;
        max-width: 180px;
    }

    #sidebar QPushButton {
        background-color: transparent;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 8px;
        padding: 10px 10px 8px 10px;
        margin: 3px 6px;
        min-height: 42px;
        font-size: 14px;
        font-weight: bold;
        color: #5a5a5a;
        text-align: center;
    }

    #sidebar QPushButton:hover {
        background-color: #dde0dd;
        color: #1a1d1a;
        border-left: 3px solid #00A844;
    }

    #sidebar QPushButton:checked,
    #sidebar QPushButton:selected {
        background-color: #00A844;
        color: #FFFFFF;
        border-left: 3px solid #00C853;
        font-weight: bold;
    }

    #sidebar QPushButton:disabled {
        color: #00A844;
        background-color: transparent;
        font-size: 13px;
        font-weight: bold;
        border-bottom: 1px solid #d5d9d5;
        border-radius: 0;
        margin: 4px 8px 12px 8px;
        padding: 10px 10px 6px 10px;
    }

    /* ==================== 卡片 ==================== */
    #taskCard {
        background-color: #f2f4f2;
        border: 1px solid #dde0dd;
        border-radius: 10px;
        padding: 14px;
        margin: 4px 8px;
    }

    #taskCard:hover {
        background-color: #f0f5f0;
        border-color: #00A844;
    }

    /* ==================== 系统信息栏 ==================== */
    #systemInfoBar {
        background-color: #ebedeb;
        border-radius: 8px;
        border: 1px solid #dde0dd;
    }

    #sysInfoItem {
        color: #4a504a;
        font-size: 14px;
    }

    #sysInfoItemOk {
        color: #00873E;
        font-size: 14px;
    }

    #sysInfoItemErr {
        color: #C62828;
        font-size: 14px;
    }

    #sysInfoSep {
        color: #c0c5c0;
        font-size: 16px;
        padding: 0 4px;
    }

    /* ==================== 统计卡片 ==================== */
    #statCardTitle {
        color: #555555;
        font-size: 14px;
    }

    #statCardValue {
        font-size: 30px;
        font-weight: bold;
    }

    /* ==================== 任务迷你卡片 ==================== */
    #taskMiniName {
        color: #1a1d1a;
        font-size: 14px;
        font-weight: bold;
    }

    #taskMiniSite {
        color: #555555;
        font-size: 14px;
    }

    #taskMiniCount {
        color: #1565C0;
        font-size: 14px;
        font-weight: bold;
    }

    #taskMiniTime {
        color: #555555;
        font-size: 13px;
    }

    /* ==================== 首页区域 ==================== */
    #homeSectionTitle {
        color: #1a1d1a;
        font-size: 18px;
        font-weight: bold;
        padding-top: 12px;
        padding-bottom: 4px;
    }

    #homeTableHeader {
        color: #555555;
        font-size: 13px;
    }

    #homeNoData {
        color: #888888;
        font-size: 14px;
        padding: 24px;
    }

    /* ==================== 按钮 ==================== */
    QPushButton {
        background-color: #00A844;
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
        padding: 9px 24px;
        font-weight: bold;
        font-size: 14px;
        min-height: 36px;
    }

    QPushButton:hover {
        background-color: #00C853;
    }

    QPushButton:pressed {
        background-color: #008c38;
    }

    QPushButton:disabled {
        background-color: #dde0dd;
        color: #9E9E9E;
    }

    /* 次要按钮 */
    QPushButton#secondaryBtn {
        background-color: #ebedeb;
        color: #3a3a3a;
        border: 1px solid #c5c9c5;
    }

    QPushButton#secondaryBtn:hover {
        background-color: #dde0dd;
        border-color: #00A844;
        color: #1a1d1a;
    }

    QPushButton#secondaryBtn:pressed {
        background-color: #d5d9d5;
    }

    QPushButton#secondaryBtn:disabled {
        background-color: #f0f2f0;
        color: #9E9E9E;
        border-color: #dde0dd;
    }

    /* 危险按钮 */
    QPushButton#dangerBtn {
        background-color: #E53935;
        color: #FFFFFF;
    }

    QPushButton#dangerBtn:hover {
        background-color: #EF5350;
    }

    QPushButton#dangerBtn:pressed {
        background-color: #C62828;
    }

    QPushButton#dangerBtn:disabled {
        background-color: #fce4e4;
        color: #b0a0a0;
    }

    /* ==================== 输入框 ==================== */
    QLineEdit {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: 1px solid #c5c9c5;
        border-radius: 7px;
        padding: 10px 14px;
        font-size: 14px;
    }

    QLineEdit:hover {
        border-color: #9E9E9E;
    }

    QLineEdit:focus {
        border-color: #00A844;
        background-color: #f5faf5;
    }

    QTextEdit, QPlainTextEdit {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: 1px solid #c5c9c5;
        border-radius: 7px;
        padding: 10px;
    }

    QTextEdit:hover, QPlainTextEdit:hover {
        border-color: #9E9E9E;
    }

    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #cccccc;
    }

    /* 日志显示区域 — 左上直角，浅灰底护眼 */
    #logTextEdit {
        background-color: #ebedeb;
        padding: 4px;
        border-top-left-radius: 0px;
    }

    /* 日志标签页容器 — 无背景框格 */
    #logTabWidget::pane {
        background-color: transparent;
        border: none;
    }

    /* 日志标签页 — 首尾按钮加圆角 */
    #logTabWidget QTabBar::tab:first {
        border-top-left-radius: 8px;
    }
    #logTabWidget QTabBar::tab:last {
        border-top-right-radius: 8px;
    }

    /* ==================== 数字输入框 ==================== */
    QSpinBox {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: 1px solid #c5c9c5;
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 14px;
        min-height: 30px;
    }

    QSpinBox:hover {
        border-color: #00A844;
    }

    QSpinBox:focus {
        border-color: #00C853;
    }

    QSpinBox::up-button, QSpinBox::down-button {
        border: none;
        background-color: #dde0dd;
        width: 22px;
        border-radius: 3px;
        margin: 3px;
    }

    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background-color: #00A844;
    }

    /* ==================== 下拉框 ==================== */
    QComboBox {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: 1px solid #c5c9c5;
        border-radius: 7px;
        padding: 10px 14px;
        min-height: 18px;
    }

    QComboBox:hover {
        border-color: #00A844;
    }

    QComboBox:focus {
        border-color: #00C853;
    }

    QComboBox::drop-down {
        border: none;
        width: 30px;
        border-radius: 0px 7px 7px 0px;
    }

    QComboBox::drop-down:hover {
        background-color: #00A844;
    }

    QComboBox QAbstractItemView {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: 1px solid #00A844;
        border-radius: 6px;
        outline: none;
        padding: 4px;
    }

    QComboBox QAbstractItemView::item {
        padding: 10px 14px;
        border-radius: 6px;
        margin: 1px 2px;
    }

    QComboBox QAbstractItemView::item:hover {
        background-color: #00A844;
        color: #FFFFFF;
    }

    QComboBox QAbstractItemView::item:selected {
        background-color: #d5edd5;
        color: #00A844;
    }

    /* ==================== 表格 ==================== */
    QTableView, QTableWidget {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: 1px solid #d5d9d5;
        border-radius: 8px;
        gridline-color: #ebedeb;
        selection-background-color: #d5edd5;
        selection-color: #00A844;
    }

    QTableView::item, QTableWidget::item {
        padding: 9px;
        border-bottom: 1px solid #ebedeb;
    }

    QTableView::item:hover, QTableWidget::item:hover {
        background-color: #f0f5f0;
    }

    QTableView::item:alternate, QTableWidget::item:alternate {
        background-color: #f5f7f5;
    }

    QHeaderView::section {
        background-color: #ebedeb;
        color: #00A844;
        padding: 12px 10px;
        border: none;
        border-bottom: 2px solid #00A844;
        font-weight: bold;
        font-size: 13px;
    }

    /* ==================== 进度条 ==================== */
    QProgressBar {
        background-color: #ebedeb;
        border: 1px solid #d5d9d5;
        border-radius: 8px;
        text-align: center;
        color: #1a1d1a;
        font-size: 12px;
        font-weight: bold;
        min-height: 24px;
    }

    QProgressBar::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #008c38, stop:0.5 #00A844, stop:1 #00C853);
        border-radius: 6px;
    }

    /* ==================== 标签 ==================== */
    QLabel {
        color: #1a1d1a;
        background-color: transparent;
    }

    QLabel#titleLabel {
        font-size: 24px;
        font-weight: bold;
        color: #00A844;
    }

    QLabel#subtitleLabel {
        font-size: 15px;
        color: #666666;
    }

    QLabel#statusComplete {
        color: #00A844;
        font-weight: bold;
    }

    QLabel#statusRunning {
        color: #E65100;
        font-weight: bold;
    }

    QLabel#statusError {
        color: #E53935;
        font-weight: bold;
    }

    /* ==================== 分组框 ==================== */
    QGroupBox {
        background-color: #f2f4f2;
        border: 1px solid #d5d9d5;
        border-radius: 10px;
        margin-top: 18px;
        padding: 18px;
        padding-top: 28px;
        font-weight: bold;
        font-size: 15px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 6px 14px;
        color: #00A844;
        font-size: 14px;
    }

    /* ==================== 滚动条 ==================== */
    QScrollBar:vertical {
        background-color: #f5f7f5;
        width: 12px;
        border: none;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #c5c9c5;
        border-radius: 6px;
        min-height: 36px;
        margin: 2px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #9E9E9E;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #f5f7f5;
        height: 12px;
        border: none;
    }

    QScrollBar::handle:horizontal {
        background-color: #c5c9c5;
        border-radius: 6px;
        min-width: 36px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #9E9E9E;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ==================== 拆分器 ==================== */
    QSplitter::handle {
        background-color: #d5d9d5;
        width: 3px;
    }

    QSplitter::handle:hover {
        background-color: #00A844;
    }

    /* ==================== 对话框 ==================== */
    QDialog {
        background-color: #f5f7f5;
    }

    /* ==================== 页面通用 ==================== */
    #pageTitle {
        color: #00873E;
        font-size: 24px;
        font-weight: bold;
    }

    #dataTablePageLabel {
        color: #555555;
        font-size: 12px;
    }

    #settingsStatusHint {
        color: #555555;
        font-size: 12px;
    }

    #taskDetailInfo {
        color: #3a3f3a;
        font-size: 14px;
        line-height: 1.6;
    }

    #progressMessage {
        color: #555555;
        font-size: 13px;
    }

    #dialogTitle {
        color: #00873E;
        font-size: 18px;
        font-weight: bold;
    }

    #dialogDesc {
        color: #4a504a;
        font-size: 13px;
    }

    #dialogLabel {
        color: #1a1d1a;
        font-size: 14px;
    }

    #dialogHighlight {
        color: #00873E;
        font-size: 14px;
        font-weight: bold;
    }

    #dialogStatus {
        color: #666666;
        font-size: 12px;
    }

    /* ==================== 消息框 ==================== */
    QMessageBox {
        background-color: #f5f7f5;
    }

    QMessageBox QLabel {
        color: #1a1d1a;
        font-size: 14px;
    }

    QMessageBox QPushButton {
        min-width: 90px;
        min-height: 34px;
    }

    /* ==================== 复选框 ==================== */
    QCheckBox {
        spacing: 10px;
        padding: 3px 0;
        font-size: 15px;
        background-color: transparent;
    }

    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid #c5c9c5;
        background-color: #f2f4f2;
    }

    QCheckBox::indicator:hover {
        border-color: #00A844;
    }

    QCheckBox::indicator:checked {
        background-color: #00A844;
        border-color: #00A844;
    }

    QCheckBox::indicator:checked:hover {
        background-color: #00C853;
        border-color: #00C853;
    }

    QCheckBox:hover {
        color: #1a1d1a;
    }

    /* ==================== 单选框 ==================== */
    QRadioButton {
        spacing: 10px;
        padding: 3px 0;
        font-size: 15px;
    }

    QRadioButton::indicator {
        width: 20px;
        height: 20px;
        border-radius: 10px;
        border: 2px solid #c5c9c5;
        background-color: #f2f4f2;
    }

    QRadioButton::indicator:hover {
        border-color: #00A844;
    }

    QRadioButton::indicator:checked {
        background-color: #00A844;
        border-color: #00A844;
    }

    QRadioButton::indicator:checked:hover {
        background-color: #00C853;
        border-color: #00C853;
    }

    QRadioButton:hover {
        color: #1a1d1a;
    }

    /* ==================== Tab 控件 ==================== */
    QTabWidget::pane {
        background-color: #f2f4f2;
        border: 1px solid #d5d9d5;
        border-top: none;
        border-radius: 0px 0px 8px 8px;
    }

    QTabBar::tab {
        background-color: #ebedeb;
        color: #666666;
        padding: 12px 22px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 15px;
    }

    QTabBar::tab:selected {
        color: #00A844;
        border-bottom: 2px solid #00A844;
    }

    QTabBar::tab:hover {
        color: #1a1d1a;
        background-color: #dde0dd;
    }

    /* ==================== 列表视图 ==================== */
    QListView {
        background-color: #f2f4f2;
        border: none;
        outline: none;
    }

    QListView::item {
        padding: 10px;
        border-bottom: 1px solid #ebedeb;
    }

    QListView::item:selected {
        background-color: #d5edd5;
        color: #00A844;
        border-radius: 6px;
    }

    QListView::item:hover {
        background-color: #f0f5f0;
        border-radius: 6px;
    }

    /* ==================== 提示框 ==================== */
    QToolTip {
        background-color: #f2f4f2;
        color: #1a1d1a;
        border: none;
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 13px;
    }
    """


# 主题名称映射
THEME_STYLESHEETS = {
    "dark": get_dark_forest_stylesheet,
    "light": get_light_stylesheet,
}

THEME_DISPLAY_NAMES = {
    "dark": "暗夜绿 (深色)",
    "light": "晨曦绿 (浅色)",
    "auto": "跟随系统",
}

# 日志级别颜色：暗色 / 浅色各一套
LOG_COLORS = {
    "dark": {
        "DEBUG": "#42A5F5",
        "INFO": "#00E676",
        "WARNING": "#FFB74D",
        "ERROR": "#EF5350",
        "CRITICAL": "#FF1744",
    },
    "light": {
        "DEBUG": "#1565C0",
        "INFO": "#00A844",
        "WARNING": "#E65100",
        "ERROR": "#C62828",
        "CRITICAL": "#6A1B9A",
    },
}
