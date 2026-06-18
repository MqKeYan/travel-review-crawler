"""
模块名称：首页/数据看板

功能说明：
    - 系统信息栏（版本、运行时间、数据目录、Cookie数、磁盘空间等）
    - 统计卡片（总任务、运行中、已完成、出错数等）
    - 最近任务卡片列表（名称、网站、评论数、创建时间、状态）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class SystemInfoBar(QFrame):
    """首页顶部系统信息栏，横向展示实用系统信息"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("systemInfoBar")
        self.setFixedHeight(36)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(0)

        # 各信息项 (key -> label widget)
        self._info_labels: dict[str, QLabel] = {}

        # 信息项顺序：版本号、运行目录(含可写)、Cookie、磁盘、启动时间、运行时间
        items = [
            "version",
            "data_dir",
            "cookies",
            "disk",
            "started_at",
            "runtime",
        ]

        for i, key in enumerate(items):
            # 分隔线（首项不加）
            if i > 0:
                sep = QLabel("│")
                sep.setStyleSheet("color: #3A3A3A; font-size: 14px;")
                sep.setFixedWidth(20)
                sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(sep)

            label = QLabel()
            label.setFont(QFont("微软雅黑", 9))
            label.setStyleSheet("color: #AAAAAA;")
            self._info_labels[key] = label
            layout.addWidget(label)

        layout.addStretch()
        self.setLayout(layout)

        # 应用样式
        self.setStyleSheet("""
            #systemInfoBar {
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 6px;
                border: 1px solid #2A2A2A;
            }
        """)

    def update_info(self, status: dict) -> None:
        """更新所有信息项显示"""
        version = status.get("version", "")
        runtime = status.get("runtime", "")
        data_dir = status.get("data_dir", "")
        writable = status.get("data_dir_writable", True)
        cookie_count = status.get("cookie_count", 0)
        disk_free = status.get("disk_free_gb", 0)
        started_at = status.get("started_at", "")

        # 版本号
        self._info_labels["version"].setText(f"版本号：v{version}")

        # 运行目录 + 可写状态（合并）
        short_dir = self._truncate_path(data_dir, 28)
        if writable:
            self._info_labels["data_dir"].setText(f"运行目录：{short_dir} (可写)")
            self._info_labels["data_dir"].setStyleSheet("color: #00E676;")
        else:
            self._info_labels["data_dir"].setText(f"运行目录：{short_dir} (只读)")
            self._info_labels["data_dir"].setStyleSheet("color: #FF5252;")
        self._info_labels["data_dir"].setToolTip(data_dir)

        # Cookie 数量
        self._info_labels["cookies"].setText(f"Cookie：{cookie_count} 个")

        # 磁盘剩余空间
        disk_color = "#FF5252" if disk_free < 1 else "#AAAAAA"
        self._info_labels["disk"].setText(f"磁盘剩余：{disk_free} GB")
        if disk_free < 1:
            self._info_labels["disk"].setStyleSheet(f"color: {disk_color};")

        # 启动时间
        self._info_labels["started_at"].setText(f"启动于：{started_at}")

        # 运行时间
        self._info_labels["runtime"].setText(f"运行时间：{runtime}")

    @staticmethod
    def _truncate_path(path: str, max_len: int) -> str:
        """截断过长路径，保留首尾"""
        if len(path) <= max_len:
            return path
        return path[:max_len - 3] + "..."


class StatCard(QFrame):
    """统计卡片组件"""

    def __init__(self, title: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.setMinimumHeight(90)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self._value_label = QLabel(value)
        self._value_label.setFont(QFont("微软雅黑", 26, QFont.Weight.Bold))
        self._value_label.setStyleSheet(f"color: {color};")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #999999; font-size: 12px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._value_label)
        layout.addWidget(title_label)
        self.setLayout(layout)

    def update_value(self, value: str) -> None:
        self._value_label.setText(value)


class TaskMiniCard(QFrame):
    """最近任务迷你卡片"""

    STATUS_COLORS = {
        "待开始": "#666666",
        "运行中": "#FFAB00",
        "已完成": "#00E676",
        "已暂停": "#FFAB00",
        "出错": "#FF5252",
        "已取消": "#666666",
    }

    def __init__(self, task_name: str, site: str, reviews: int, created_at: str,
                 status_cn: str, parent=None):
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.setFixedHeight(72)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # 任务名
        name_label = QLabel(task_name)
        name_label.setFont(QFont("微软雅黑", 12, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #E0E0E0;")
        name_label.setMinimumWidth(120)

        # 网站
        site_label = QLabel(site)
        site_label.setStyleSheet("color: #999999; font-size: 12px;")
        site_label.setMinimumWidth(60)

        # 评论数
        count_label = QLabel(f"{reviews} 条")
        count_label.setStyleSheet("color: #448AFF; font-size: 12px;")
        count_label.setMinimumWidth(50)

        # 时间
        time_label = QLabel(created_at)
        time_label.setStyleSheet("color: #666666; font-size: 11px;")
        time_label.setMinimumWidth(140)

        # 状态
        color = self.STATUS_COLORS.get(status_cn, "#666666")
        status_label = QLabel(status_cn)
        status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        status_label.setMinimumWidth(50)

        layout.addWidget(name_label)
        layout.addWidget(site_label)
        layout.addWidget(count_label)
        layout.addWidget(time_label)
        layout.addWidget(status_label)
        layout.addStretch()
        self.setLayout(layout)


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
        layout.addWidget(self._system_info_bar)

        # ---- 统计卡片 ----
        card_layout = QGridLayout()
        card_layout.setSpacing(12)

        self._stat_total = StatCard("总任务", "0", "#00C853")
        self._stat_running = StatCard("运行中", "0", "#FFAB00")
        self._stat_completed = StatCard("已完成", "0", "#00E676")
        self._stat_errors = StatCard("出错", "0", "#FF5252")
        self._stat_reviews = StatCard("总评论数", "0", "#448AFF")
        self._stat_sites = StatCard("使用网站", "0", "#FF6D00")
        self._stat_rate = StatCard("完成率", "0%", "#00BCD4")

        card_layout.addWidget(self._stat_total, 0, 0)
        card_layout.addWidget(self._stat_running, 0, 1)
        card_layout.addWidget(self._stat_completed, 0, 2)
        card_layout.addWidget(self._stat_errors, 0, 3)
        card_layout.addWidget(self._stat_reviews, 1, 0)
        card_layout.addWidget(self._stat_sites, 1, 1)
        card_layout.addWidget(self._stat_rate, 1, 2)

        layout.addLayout(card_layout)

        # ---- 最近任务标题 ----
        recent_label = QLabel("最近任务")
        recent_label.setFont(QFont("微软雅黑", 15, QFont.Weight.Bold))
        recent_label.setStyleSheet("color: #E0E0E0; padding-top: 8px;")
        layout.addWidget(recent_label)

        # 表头
        header = QHBoxLayout()
        header.setSpacing(16)
        header.setContentsMargins(24, 4, 16, 4)
        for h in ["任务名称", "网站", "评论数", "创建时间", "状态"]:
            lbl = QLabel(h)
            lbl.setStyleSheet("color: #666666; font-size: 11px;")
            if h == "任务名称":
                lbl.setMinimumWidth(120)
            elif h == "网站":
                lbl.setMinimumWidth(60)
            elif h == "评论数":
                lbl.setMinimumWidth(50)
            elif h == "创建时间":
                lbl.setMinimumWidth(140)
            elif h == "状态":
                lbl.setMinimumWidth(50)
            header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        # 任务卡片容器
        self._recent_container = QVBoxLayout()
        self._recent_container.setSpacing(4)
        self._no_task_label = QLabel("暂无任务数据")
        self._no_task_label.setStyleSheet("color: #666666; font-size: 13px; padding: 20px;")
        self._no_task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_container.addWidget(self._no_task_label)
        layout.addLayout(self._recent_container)

        layout.addStretch()
        self.setLayout(layout)

    def update_system_info(self, status: dict) -> None:
        """更新系统信息栏显示"""
        self._system_info_bar.update_info(status)

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
            self._no_task_label.setStyleSheet("color: #666666; font-size: 13px; padding: 20px;")
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
