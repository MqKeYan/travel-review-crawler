"""
模块名称：首页/数据看板

功能说明：
    - 系统信息栏（版本、运行时间、数据目录、Cookie数、磁盘空间等）
    - 统计卡片（总任务、运行中、已完成、出错数等）
    - 最近任务卡片列表（名称、网站、评论数、创建时间、状态）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QCursor

from src.ui.components.task_card import _ElidedLabel


class SystemInfoBar(QFrame):
    """首页顶部系统信息栏，双行展示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("systemInfoBar")
        self.setFixedHeight(68)

        outer = QVBoxLayout()
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(6)

        self._info_labels: dict[str, QLabel] = {}

        # ---- 第一行：版本 | 运行目录 | Cookie | 启动时间 | 运行时间 ----
        row1 = QHBoxLayout()
        row1.setSpacing(0)
        self._build_row(row1, ["version", "data_dir", "started_at", "runtime"])
        outer.addLayout(row1)

        # ---- 第二行：CPU | 内存 | 软件占用 | 硬盘剩余 | 代理 | 延迟 ----
        row2 = QHBoxLayout()
        row2.setSpacing(0)
        self._build_row(row2, ["cpu", "memory", "app_disk", "disk_free", "proxy"])
        outer.addLayout(row2)

        self.setLayout(outer)

    def _build_row(self, row: QHBoxLayout, keys: list[str]) -> None:
        for i, key in enumerate(keys):
            if i > 0:
                sep = QLabel("│")
                sep.setObjectName("sysInfoSep")
                sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row.addWidget(sep)
            label = QLabel()
            label.setFont(QFont("微软雅黑", 14))
            label.setObjectName("sysInfoItem")
            self._info_labels[key] = label
            row.addWidget(label)
        row.addStretch()

    def update_info(self, status: dict) -> None:
        version = status.get("version", "")
        runtime = status.get("runtime", "")
        data_dir = status.get("data_dir", "")
        writable = status.get("data_dir_writable", True)
        memory_mb = status.get("memory_mb", 0)
        app_disk_mb = status.get("app_disk_mb", 0)
        disk_free = status.get("disk_free_gb", 0)
        started_at = status.get("started_at", "")

        # === 第一行 ===
        self._info_labels["version"].setText(f"版本号：v{version}")

        short_dir = self._truncate_path(data_dir, 28)
        if writable:
            self._info_labels["data_dir"].setText(
                f"运行目录：{short_dir} <span style='color:#00873E'>(可写)</span>")
        else:
            self._info_labels["data_dir"].setText(
                f"运行目录：{short_dir} <span style='color:#C62828'>(只读)</span>")
        self._info_labels["data_dir"].setStyleSheet("")
        self._info_labels["data_dir"].setToolTip(data_dir)

        self._info_labels["started_at"].setText(f"启动时间：{started_at}")
        self._info_labels["runtime"].setText(f"运行时间：{runtime}")

        # === 第二行 ===
        cpu_percent = status.get("cpu_percent", 0)
        self._info_labels["cpu"].setText(f"CPU：{cpu_percent}%")

        if memory_mb >= 1024:
            self._info_labels["memory"].setText(f"内存：{memory_mb/1024:.1f} GB")
        else:
            self._info_labels["memory"].setText(f"内存：{memory_mb} MB")

        if app_disk_mb >= 1024:
            self._info_labels["app_disk"].setText(f"软件占用：{app_disk_mb/1024:.1f} GB")
        else:
            self._info_labels["app_disk"].setText(f"软件占用：{app_disk_mb} MB")

        self._info_labels["disk_free"].setText(f"硬盘剩余：{disk_free} GB")
        if disk_free < 1:
            self._info_labels["disk_free"].setStyleSheet("color: #C62828; font-size: 14px;")

        proxy_enabled = status.get("proxy_enabled", False)
        if proxy_enabled:
            self._info_labels["proxy"].setText("代理：已启用")
            self._info_labels["proxy"].setStyleSheet("color: #00A844; font-size: 14px;")
        else:
            self._info_labels["proxy"].setText("代理：关闭")

    @staticmethod
    def _truncate_path(path: str, max_len: int) -> str:
        if len(path) <= max_len:
            return path
        return path[:max_len - 3] + "..."


class StatCard(QFrame):
    """统计卡片组件"""

    def __init__(self, title: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.setMinimumHeight(100)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(2)

        self._value_label = QLabel(value)
        self._value_label.setFont(QFont("微软雅黑", 30, QFont.Weight.Bold))
        self._value_label.setObjectName("statCardValue")
        self._value_label.setProperty("statColor", color)
        self._value_label.setStyleSheet(f"color: {color};")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("statCardTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._value_label)
        layout.addSpacing(2)
        layout.addWidget(title_label)
        self.setLayout(layout)

    def update_value(self, value: str) -> None:
        self._value_label.setText(value)


class TaskMiniCard(QFrame):
    """最近任务迷你卡片"""

    STATUS_COLORS = {
        "待开始": "#555555",
        "运行中": "#FFAB00",
        "已完成": "#00A844",
        "已暂停": "#FFAB00",
        "出错": "#D32F2F",
        "已取消": "#555555",
    }

    def __init__(self, task_name: str, site: str, reviews: int, created_at: str,
                 status_cn: str, parent=None):
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.setFixedHeight(76)
        self.setMinimumWidth(0)

        # 悬停 1 秒后弹出任务名称提示（与任务列表卡片逻辑一致）
        self._task_name = task_name
        self._tip_label: QLabel | None = None
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(1000)
        self._hover_timer.timeout.connect(self._show_hover_tip)
        self.setMouseTracking(True)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # 任务名（弹性占位，长名称自动省略，不挤压其他列）
        name_label = _ElidedLabel(task_name)
        name_label.setFont(QFont("微软雅黑", 14, QFont.Weight.Bold))
        name_label.setObjectName("taskMiniName")
        name_label.setMinimumWidth(0)
        name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        # 网站
        site_label = QLabel(site)
        site_label.setObjectName("taskMiniSite")
        site_label.setMinimumWidth(0)

        # 评论数
        count_label = QLabel(f"{reviews} 条")
        count_label.setObjectName("taskMiniCount")

        # 时间
        time_label = QLabel(created_at)
        time_label.setObjectName("taskMiniTime")

        # 状态
        color = self.STATUS_COLORS.get(status_cn, "#555555")
        status_label = QLabel(status_cn)
        status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")

        layout.addWidget(name_label, 1)
        layout.addWidget(site_label, 1)
        layout.addWidget(count_label, 1)
        layout.addWidget(time_label, 2)
        layout.addWidget(status_label, 1)
        self.setLayout(layout)

    def enterEvent(self, event) -> None:
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
        if self._tip_label is None:
            self._tip_label = QLabel(self.window())
            self._tip_label.setWindowFlags(Qt.WindowType.ToolTip)
            self._tip_label.setFont(QFont("微软雅黑", 13))
            self._tip_label.setStyleSheet(
                "background-color: #1f231f; color: #E8E8E8;"
                "padding: 6px 10px; border-radius: 6px;"
            )
        self._tip_label.setText(f"任务名称：{self._task_name}")
        self._tip_label.adjustSize()
        pos = QCursor.pos()
        self._tip_label.move(pos.x() - self._tip_label.width() // 2, pos.y() - self._tip_label.height())
        self._tip_label.show()

    def _hide_tip(self) -> None:
        if self._tip_label:
            self._tip_label.hide()


class HomePage(QWidget):
    """首页/数据看板页面"""

    navigate = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 12, 24, 20)
        layout.setSpacing(12)

        # ---- 系统信息栏 ----
        self._system_info_bar = SystemInfoBar()
        bar_container = QHBoxLayout()
        bar_container.setContentsMargins(8, 0, 8, 0)
        bar_container.addWidget(self._system_info_bar)
        layout.addLayout(bar_container)

        # ---- 统计卡片 ----
        card_layout = QGridLayout()
        card_layout.setSpacing(12)

        self._stat_total = StatCard("总任务", "0", "#00873E")
        self._stat_running = StatCard("运行中", "0", "#E65100")
        self._stat_completed = StatCard("已完成", "0", "#00A844")
        self._stat_errors = StatCard("出错", "0", "#D32F2F")
        self._stat_cookies = StatCard("Cookie 数量", "0", "#6A1B9A")
        self._stat_reviews = StatCard("总评论数", "0", "#1565C0")
        self._stat_sites = StatCard("使用网站", "0", "#BF360C")
        self._stat_rate = StatCard("完成率", "0%", "#00838F")

        card_layout.addWidget(self._stat_total, 0, 0)
        card_layout.addWidget(self._stat_running, 0, 1)
        card_layout.addWidget(self._stat_completed, 0, 2)
        card_layout.addWidget(self._stat_errors, 0, 3)
        card_layout.addWidget(self._stat_cookies, 1, 0)
        card_layout.addWidget(self._stat_reviews, 1, 1)
        card_layout.addWidget(self._stat_sites, 1, 2)
        card_layout.addWidget(self._stat_rate, 1, 3)

        layout.addLayout(card_layout)

        # ---- 最近任务标题（居中） ----
        recent_label = QLabel("最近任务")
        recent_label.setFont(QFont("微软雅黑", 18, QFont.Weight.Bold))
        recent_label.setObjectName("homeSectionTitle")
        recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(recent_label)

        # 表头（与 TaskMiniCard 列宽比例一致: 1:1:1:2:1）
        header = QHBoxLayout()
        header.setSpacing(16)
        header.setContentsMargins(38, 2, 38, 4)
        header_stretches = [1, 1, 1, 2, 1]
        for i, h in enumerate(["任务名称", "网站", "评论数", "创建时间", "状态"]):
            lbl = QLabel(h)
            lbl.setObjectName("homeTableHeader")
            header.addWidget(lbl, header_stretches[i])
        layout.addLayout(header)

        # 任务卡片容器
        self._recent_container = QVBoxLayout()
        self._recent_container.setSpacing(4)
        self._no_task_label = QLabel("暂无任务数据")
        self._no_task_label.setObjectName("homeNoData")
        self._no_task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_container.addWidget(self._no_task_label)
        layout.addLayout(self._recent_container)

        layout.addStretch()
        self.setLayout(layout)

    def update_system_info(self, status: dict) -> None:
        """更新系统信息栏显示 + Cookie 统计卡片"""
        self._system_info_bar.update_info(status)
        cookie_count = status.get("cookie_count", 0)
        self._stat_cookies.update_value(str(cookie_count))

    def update_stats(self, stats: dict) -> None:
        """更新看板统计信息和最近任务列表"""
        self._stat_total.update_value(str(stats.get("total", 0)))
        self._stat_running.update_value(str(stats.get("running", 0)))
        self._stat_completed.update_value(str(stats.get("completed", 0)))
        self._stat_errors.update_value(str(stats.get("error", 0)))
        self._stat_reviews.update_value(str(stats.get("total_reviews", 0)))
        self._stat_sites.update_value(str(stats.get("used_sites", 0)))
        self._stat_rate.update_value(f"{stats.get('completion_rate', 0)}%")

        # 更新最近任务卡片
        self._update_recent_tasks(stats.get("recent_tasks", []))

    def _update_recent_tasks(self, tasks: list[dict]) -> None:
        """更新最近任务卡片列表"""
        # 清空旧卡片
        while self._recent_container.count():
            item = self._recent_container.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not tasks:
            self._no_task_label = QLabel("暂无任务数据")
            self._no_task_label.setObjectName("homeNoData")
            self._no_task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._recent_container.addWidget(self._no_task_label)
            return

        for t in tasks:
            card = TaskMiniCard(
                task_name=t.get("name", ""),
                site=t.get("site", ""),
                reviews=t.get("reviews", 0),
                created_at=t.get("created_at", ""),
                status_cn=t.get("status", ""),
            )
            self._recent_container.addWidget(card)
