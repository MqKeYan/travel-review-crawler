# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# ============================================================
# 第三方库子模块收集（解决 importlib 动态导入和复杂包结构问题）
# ============================================================

# Selenium — 自动收集所有子模块（解决 importlib 动态导入问题）
selenium_hidden = collect_submodules('selenium')
# Selenium 数据文件（包含 selenium-manager.exe 浏览器驱动管理器）
selenium_datas = collect_data_files('selenium')

# beautifulsoup4 → bs4
bs4_hidden = collect_submodules('bs4')

# urllib3 — requests 底层 HTTP 库，SSL/连接池/重试等子模块
urllib3_hidden = collect_submodules('urllib3')

# python-docx — Word 文档读写，oxml/enum/shared 等大量内部子模块
docx_hidden = collect_submodules('docx')

# openpyxl — Excel 读写，styles/drawing/utils 等子模块
openpyxl_hidden = collect_submodules('openpyxl')

# fake_useragent — UA 数据库 + 版本管理子模块
fake_ua_hidden = collect_submodules('fake_useragent')
fake_ua_datas = collect_data_files('fake_useragent')

# certifi — SSL 证书文件（requests HTTPS 必需）
certifi_datas = collect_data_files('certifi')

# ============================================================
# 输出路径：将最终打包产物从默认的 dist/ 改为 build/
# ============================================================
import PyInstaller.config
PyInstaller.config.CONF['distpath'] = 'build'

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/ui/theme', 'ui/theme'),
        ('src/assets', 'assets'),
    ] + selenium_datas + fake_ua_datas + certifi_datas,
    hiddenimports=[
        # ---- PySide6 框架 ----
        'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtMultimedia',
        # ---- HTTP 网络与解析 ----
        'requests', 'urllib3', 'certifi', 'charset_normalizer',
        'lxml',
        # ---- 文件导出 ----
        'openpyxl', 'docx',
        # ---- 图像处理（验证码自动求解） ----
        'PIL', 'numpy',
        # ---- 系统监控（CPU/内存） ----
        'psutil',
        # ---- 并发执行（图片下载线程池） ----
        'concurrent.futures',
        # ---- Windows 多进程支持（freeze_support） ----
        'multiprocessing',
        # ---- 浏览器本地 Cookie 读取（备用方案） ----
        'browser_cookie3',
    ] + selenium_hidden + bs4_hidden + urllib3_hidden + docx_hidden + openpyxl_hidden + fake_ua_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='tour-crawler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src\\assets\\app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='tour-crawler',
)
