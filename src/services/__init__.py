"""
服务层包，封装业务逻辑，供 UI 层调用。

所有服务类为单例模式，由应用入口（main.py）统一初始化。
UI 层通过直接调用服务层方法通信，
耗时操作通过 QThread + Qt Signal 实现异步，不阻塞 UI。

服务类清单：
    - CookieService: Cookie 获取与读取
    - TaskService: 爬取任务管理
    - DataService: 评论数据查询与缓存
    - ExportService: 数据导出
    - SiteService: 网站配置
    - SystemService: 系统设置
"""

from src.services.cookie_service import CookieService
from src.services.task_service import TaskService
from src.services.data_service import DataService
from src.services.export_service import ExportService
from src.services.site_service import SiteService
from src.services.system_service import SystemService

__all__ = [
    "CookieService", "TaskService", "DataService",
    "ExportService", "SiteService", "SystemService",
]
