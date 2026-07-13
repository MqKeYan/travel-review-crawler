<h1 align="center">
  <br>
  <strong>🦀 评价爬虫器——旅游评论采集工具</strong>
  <br>
</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue"></a>
  <a href="#"><img src="https://img.shields.io/badge/Release-v0.5.0-brightgreen"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-lightgrey"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white"></a>
  <a href="#"><img src="https://img.shields.io/badge/PySide6-6.8+-41CD52?logo=qt&logoColor=white"></a>
  <a href="#"><img src="https://img.shields.io/badge/NumPy-1.26+-013243?logo=numpy&logoColor=white"></a>
</p>

<p align="center">
  <strong> 支持携程、飞猪等旅游平台，一键爬取景区评论数据 </strong>
</p>

## 功能概览

| 功能 | 说明 |
|------|------|
| 🌐 多平台支持 | 携程(景点/酒店)、飞猪、淘宝/天猫，预设站点适配器 |
| 🍪 Cookie 管理 | 一键拉取系统浏览器（Edge / Chrome / Firefox）的登录 Cookie，按平台分类存储 |
| 🖼️ 图片下载 | 评论图片多线程下载到本地，DOCX 导出时自动嵌入 |
| 📤 多格式导出 | TXT · CSV · XLSX · DOCX，支持关键字过滤、图片过滤、纯表情过滤 |
| 🔔 任务通知 | 桌面弹窗 + 声音提示 + PushPlus 微信推送 |
| 🎨 双主题 | 暗夜绿（暗色）/ 晨曦绿（亮色）/ 跟随系统，窗口标题栏同步 |
| 🧵 异步爬取 | QThread + Signal/Slot，爬取不卡 UI，支持暂停/恢复/停止 |
| ⏸️ 断点续爬 | 任务进度自动保存，重启后可从中断位置继续 |

## 平台支持矩阵

| 平台 | 爬取模式 | 验证码处理 |
|------|----------|-----------|
| 携程(景点) | requests（首页）+ Selenium 点击翻页（后续页） | 暂未发现需求 |
| 飞猪 | Selenium 滚动加载 | 滑块自动过 |
| 淘宝/天猫 | Selenium 滚动加载 | 手动处理 |
| 携程(酒店) | requests（首页）+ Selenium 翻页 | 暂未发现需求 |

## 系统要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows 10 版本 1809 及以上 / Windows 11 |
| 架构 | 64 位（x64） |
| 内存 | 建议 4GB 及以上 |
| 浏览器 | Edge / Chrome / Firefox（仅 Cookie 获取时需要） |

## 快速开始

### 下载 & 运行

1. 从 [Releases](../../releases) 页面下载最新版 `.7z`压缩包
2. 解压到任意目录（**不要放在需要管理员权限的目录**，如 `C:\Program Files`）
3. 注意 `tour-crawler.exe` 需要和 `_internal/` 文件夹在同一目录
4. 双击运行 `tour-crawler.exe` 文件即可启动软件

> 首次启动会自动创建 `cookies/`、`logs/`、`exports/`、`tasks/` 等运行时文件夹。

### 从源码运行

```bash
# 环境要求：Python 3.13+
git clone https://github.com/MqKeYan/travel-review-crawler.git
cd travel-review-crawler
pip install -r requirements.txt --upgrade
cd src && python main.py
```

### 打包为 exe

```bash
PyInstaller tour-crawler.spec
```

## 界面截图

| 暗夜绿（暗色主题） | 晨曦绿（浅色主题） |
|:---:|:---:|
| ![暗色主题](Screenshots/dark.png) | ![浅色主题](Screenshots/light.png) |

## 使用流程

1. **获取 Cookie**：首页点击「获取 Cookie」，选择目标平台，软件自动打开系统浏览器到登录页，登录后自动提取
2. **新建任务**：选择爬取网站、输入目标 URL（或景点 ID）、设置爬取条数和页数、选择过滤规则
3. **启动爬取**：任务列表点击「开始」，实时查看进度和速度
4. **数据导出**：切换到数据页面，选择任务，导出为 TXT / CSV / XLSX / DOCX

## 项目结构

```
src/                                # 源代码根目录
├── main.py                         # 应用入口，初始化 QApplication、主题、托盘
├── __init__.py                     # 版本号
│
├── engine/                         # 爬虫核心引擎
│   ├── browser.py                  # 浏览器驱动封装：Selenium WebDriver 生命周期管理
│   ├── crawler.py                  # 通用爬虫引擎：分页、重试、UA 伪装、Cookie 注入
│   ├── cookie_manager.py           # Cookie 管理：拉取系统浏览器本地 Cookie 数据库
│   ├── captcha_handler.py           # 验证码检测与用户手动处理调度
│   ├── image_downloader.py         # 评论图片批量下载：多线程并发、自动重试
│   ├── ua_spoofer.py               # User-Agent 随机伪装池
│   └── notifier.py                 # 桌面通知 + PushPlus 微信推送
│
├── sites/                          # 网站适配器（按爬取类型/目标网站二级目录）
│   ├── base.py                     # 抽象基类 SiteAdapter，定义统一接口
│   ├── __init__.py                 # 适配器注册表 + URL 自动识别爬取类型
│   ├── scenic/                     # 旅游景点分类
│   │   ├── __init__.py             # register_adapters() 聚合入口
│   │   ├── ctrip.py                # 携程景区：requests 首页 + Selenium 翻页
│   │   └── fliggy.py               # 飞猪景区：Selenium 滚动加载 + 滑块验证码
│   ├── hotel/                      # 酒店民宿分类
│   │   ├── __init__.py             # register_adapters() 聚合入口
│   │   └── ctrip_hotel.py          # 携程酒店：requests 首页 + Selenium 翻页
│   └── shopping/                   # 购物网站分类
│       ├── __init__.py             # register_adapters() 聚合入口
│       └── taobao.py               # 淘宝/天猫：Selenium 滚动翻页 + 时间排序 + 评论侧边面板
│
├── ui/                             # PySide6 桌面界面层
│   ├── main_window.py              # 暗夜绿三栏主窗口 + QSystemTrayIcon 系统托盘
│   │
│   ├── pages/                      # 页面模块
│   │   ├── home_page.py            # 首页仪表盘：系统信息栏 + 统计卡片 + 最近任务
│   │   ├── task_page.py            # 任务管理：任务列表 + 操作按钮（开始/暂停/停止/删除）
│   │   ├── create_task_page.py     # 新建任务：站点选择、URL 输入、参数配置、Cookie 获取
│   │   ├── data_page.py            # 数据查看与导出：表格浏览 + 格式选择
│   │   ├── log_page.py             # 日志查看：实时日志流 + 按级别过滤 + 自动滚动
│   │   └── settings_page.py        # 系统设置：主题切换、代理、导出路径、任务默认值
│   │
│   ├── components/                 # 可复用 UI 组件
│   │   ├── sidebar.py              # 侧边栏导航
│   │   ├── task_card.py            # 任务卡片：进度条 + 状态标签 + 操作按钮
│   │   ├── progress_bar.py         # 爬取进度条：百分比 + 速度 + ETA
│   │   ├── data_table.py           # 数据表格：QAbstractTableModel + 排序 + 分页
│   │   └── cookie_dialog.py        # Cookie 获取对话框：打开浏览器 → 登录 → 提取
│   │
│   └── theme/                      # 主题引擎
│       └── dark_forest_theme.py    # 暗夜绿 + 晨曦绿双主题 QSS + Windows DWM 标题栏同步
│
├── services/                       # 业务逻辑服务层
│   ├── task_service.py             # 任务生命周期管理：创建/启动/暂停/恢复/停止/删除
│   ├── data_service.py             # 评论数据存储与查询，未导出数据追踪
│   ├── cookie_service.py           # Cookie 提取/保存/加载/清除，按平台隔离
│   ├── export_service.py           # 导出调度：同步/异步导出，QThread 异步不卡 UI
│   ├── log_service.py              # 日志服务：日志收集、分发与持久化
│   ├── system_service.py           # 系统设置读写，Windows 主题注册表检测
│   ├── site_service.py             # 站点列表查询，URL 自动识别与模板拼接
│   ├── stats_service.py            # 运行统计：使用时长、完成任务数
│   └── __init__.py                 # 服务层统一导出
│
├── workers/                        # QThread 异步工作线程
│   ├── crawl_worker.py             # 爬取工作线程：QThread + Signal 实时推送进度
│   ├── export_worker.py            # 导出工作线程：大数据量异步导出
│   └── __init__.py
│
├── filters/                        # 评论内容过滤器链
│   ├── base.py                     # 过滤器抽象基类 + FilterChain 责任链
│   ├── keyword_filter.py           # 敏感词 / 广告关键词过滤
│   ├── image_filter.py             # 去除图片评论 / 仅保留含图评论
│   ├── emoji_filter.py             # 去除 emoji 表情符号
│   ├── pure_emoji.py               # 纯表情评论过滤
│   └── __init__.py                 # build_filter_chain() 工厂函数
│
├── export/                         # 多格式导出器
│   ├── base.py                     # 导出器抽象基类 BaseExporter
│   ├── txt_exporter.py             # 纯文本导出
│   ├── csv_exporter.py             # CSV 表格导出
│   ├── xlsx_exporter.py            # Excel 导出，openpyxl
│   ├── docx_exporter.py            # Word 导出，内嵌图片自动缩放
│   └── __init__.py
│
├── models/                         # 数据模型
│   ├── task.py                     # Task / TaskConfig / TaskStatus 定义
│   ├── review.py                   # 评论数据结构 + 标准化字段
│   └── __init__.py
│
├── utils/                          # 工具模块
│   ├── paths.py                    # 运行目录管理：exe 目录 vs %APPDATA% 自适应
│   ├── logger.py                   # 日志系统：按日切割 + 自动清理过期日志
│   ├── image_utils.py              # 图像处理：缩放、格式转换
│   ├── url_cleaner.py              # URL 参数清洗：去除追踪参数，构造干净链接
│   ├── exceptions.py               # 自定义异常：NetworkError / ParseError / RateLimitError 等
│   └── __init__.py
│
└── assets/                         # 静态资源
    └── app.ico                     # 软件图标
```

## 讨论与交流

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;如果你在使用过程中遇到任何问题，或者有新的功能需求、改进建议，欢迎在 [GitHub Issues](../../issues) 中提出。如果你有相应的解决方法，也非常欢迎提交 Pull Request 帮助我一起完善这个项目！

## 行为准则

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;本项目遵循 **Contributor Covenant Code of Conduct**。我们致力于营造一个开放、友好、互相尊重的社区环境。

## 许可证

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;本项目采用 **GPL-3.0 License** 开源许可证。详见 [LICENSE](./LICENSE) 文件。