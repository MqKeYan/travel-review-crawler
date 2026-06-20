<h1 align="center">
  <br>
  <strong>🦀 评价爬虫器——旅游评论采集工具</strong>
  <br>
</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL3.0-green"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.13-blue"></a>
  <a href="#"><img src="https://img.shields.io/badge/PySide6-6.8+-purple"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-lightgrey"></a>
  <a href="#"><img src="https://img.shields.io/badge/Release-v0.4.1-brightgreen"></a>
  <a href="#"><img src="https://img.shields.io/badge/打包-PyInstaller-orange"></a>
</p>

<p align="center">
  Languages:
  <a href="./README.md"> 简体中文 </a>
</p>

<p align="center">
  <strong> 支持携程、去哪儿、飞猪、大众点评四大旅游平台，一键爬取景区评论数据 </strong>
  <br>
  <strong> 暗夜绿 · 晨曦绿双主题 | 滑块验证码自动求解 | 评论图片本地下载 | 多格式导出 </strong>
</p>

## 简介

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;评价爬虫器是一款基于 PySide6 构建的 Windows 桌面应用，专注于**旅游景区的用户评论数据采集**。软件通过纯 HTTP 请求 + Selenium 浏览器渲染两种模式，覆盖携程、去哪儿、飞猪、大众点评四大平台的评论爬取。内置 Cookie 管理、验证码自动求解、图片本地下载、多格式导出（TXT / CSV / XLSX / DOCX）和桌面通知推送，提供开箱即用的完整体验。

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;软件采用**暗夜绿**暗色主题与**晨曦绿**浅色主题双皮肤，支持高 DPI 自适应，适配 720P ~ 4K 分辨率，提供三栏布局的现代化桌面交互界面。

## 功能概览

| 功能 | 说明 |
|------|------|
| 🌐 多平台支持 | 携程、去哪儿、飞猪、大众点评，预设站点适配器 |
| 🍪 Cookie 管理 | 一键拉取系统浏览器（Edge / Chrome / Firefox）的登录 Cookie，按平台分类存储 |
| 🔐 验证码自动求解 | 基于 PIL/numpy 边缘检测的滑块验证码自动识别，人类轨迹模拟 |
| 🖼️ 图片下载 | 评论图片多线程下载到本地，DOCX 导出时自动嵌入 |
| 📤 多格式导出 | TXT · CSV · XLSX · DOCX，支持关键字过滤、图片过滤、纯表情过滤 |
| 🔔 任务通知 | 桌面弹窗 + 声音提示 + PushPlus 微信推送 |
| 🎨 双主题 | 暗夜绿（暗色）/ 晨曦绿（亮色）/ 跟随系统，窗口标题栏同步 |
| 🧵 异步爬取 | QThread + Signal/Slot，爬取不卡 UI，支持暂停/恢复/停止 |
| ⏸️ 断点续爬 | 任务进度自动保存，重启后可从中断位置继续 |
| 💻 Windows 专属 | 纯 Windows 10/11 64 位桌面应用，PyInstaller 打包分发 |

## 平台支持矩阵

| 平台 | 爬取模式 | 验证码处理 | 备注 |
|------|----------|-----------|------|
| 携程 | requests 翻页 | — | 纯 HTTP 请求 |
| 去哪儿 | requests 翻页 + Selenium 兜底 | — | 混合模式 |
| 飞猪 | Selenium 滚动加载 | 滑块自动求解 | headless 后台运行 |
| 大众点评 | Selenium 翻页 | — | CSS+SVG 字体解密 |

## 系统要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Windows 10 版本 1809 及以上 / Windows 11 |
| 架构 | 64 位（x64） |
| 内存 | 建议 4GB 及以上 |
| 浏览器 | Edge / Chrome / Firefox（仅 Cookie 获取时需要） |

## 快速开始

### 下载 & 运行（普通用户）

1. 从 [Releases](../../releases) 页面下载最新版 `tour-crawler.zip`
2. 解压到任意目录（**不要放在需要管理员权限的目录**，如 `C:\Program Files`）
3. 双击 `tour-crawler.exe` 启动

> 首次启动会自动创建 `cookies/`、`logs/`、`exports/`、`tasks/` 等运行时文件夹。

### 从源码运行（开发者）

```bash
# 环境要求：Python 3.13+
git clone https://github.com/MqKeYan/travel-review-crawler.git
cd travel-review-crawler
pip install -r requirements.txt --upgrade
cd src && python main.py
```

### 打包为 exe

```bash
cd travel-review-crawler
python -m PyInstaller tour-crawler.spec
# 输出目录：build/dist/tour-crawler/
```

## 界面截图

| 暗夜绿（暗色主题） | 晨曦绿（浅色主题） |
|:---:|:---:|
| ![暗色主题](screenshots/dark.png) | ![浅色主题](screenshots/light.png) |

## 使用流程

1. **获取 Cookie**：首页点击「获取 Cookie」，选择目标平台，软件自动打开系统浏览器到登录页，登录后自动提取
2. **新建任务**：选择爬取网站、输入目标 URL（或景点 ID）、设置爬取条数和页数、选择过滤规则
3. **启动爬取**：任务列表点击「开始」，实时查看进度和速度
4. **数据导出**：切换到数据页面，选择任务，导出为 TXT / CSV / XLSX / DOCX

## 项目结构

```
travel-review-crawler/
├── src/
│   ├── main.py                   # 应用入口
│   ├── ui/                       # PySide6 界面层
│   │   ├── main_window.py        # 三栏主窗口 + 系统托盘
│   │   ├── pages/                # 首页 / 任务 / 数据 / 设置
│   │   ├── components/           # 侧边栏 / 任务卡片 / 进度条 / 数据表格
│   │   └── theme/                # 暗夜绿 + 晨曦绿 QSS 主题
│   ├── engine/                   # 爬虫引擎 + Cookie 管理 + 验证码求解
│   ├── sites/                    # 携程 / 去哪儿 / 飞猪 / 大众点评适配器
│   ├── services/                 # 任务 / 数据 / 导出 / 系统设置 服务层
│   ├── workers/                  # QThread 异步工作线程
│   ├── filters/                  # 内容过滤器（关键字 / 图片 / 表情）
│   └── export/                   # TXT / CSV / XLSX / DOCX 导出器
├── tests/                        # 测试用例
├── build/dist/                   # 打包产物
└── requirements.txt              # Python 依赖清单
```

## 讨论与交流

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;如果你在使用过程中遇到任何问题，或者有新的功能需求、改进建议，欢迎在 [GitHub Issues](../../issues) 中提出。如果你有相应的解决方法，也非常欢迎提交 Pull Request 帮助我一起完善这个项目！

## 行为准则

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;本项目遵循 **Contributor Covenant Code of Conduct**。
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;我们致力于营造一个开放、友好、互相尊重的社区环境。

## 许可证

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;本项目采用 **MIT License** 开源许可证。详见 [LICENSE](./LICENSE) 文件。
