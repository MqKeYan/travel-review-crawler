# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 评价爬虫器 (Tour Crawler)

使用方式：
    pyinstaller tour-crawler.spec   ← 直接打包（通过白名单自动过滤无关库）
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from PyInstaller.building.datastruct import Tree

# ============================================================
# 第三方库子模块收集（解决 importlib 动态导入和复杂包结构问题）
# ============================================================

# Selenium — 自动收集所有子模块（解决 importlib 动态导入问题）
selenium_hidden = collect_submodules('selenium')
# Selenium 数据文件（包含 selenium-manager.exe 浏览器驱动管理器）
selenium_datas = collect_data_files('selenium')

# beautifulsoup4 → bs4
bs4_hidden = collect_submodules('bs4')

# lxml — HTML/XML 解析（BS4 通过字符串 "lxml" 动态加载 etree/html 子模块）
lxml_hidden = collect_submodules('lxml')

# requests — HTTP 客户端（内部 adapters/auth/cookies 等动态子模块）
requests_hidden = collect_submodules('requests')

# urllib3 — requests 底层 HTTP 库，SSL/连接池/重试等子模块
urllib3_hidden = collect_submodules('urllib3')

# Pillow — 图像处理（PNG/JPEG 等编解码器插件动态加载）
pil_hidden = collect_submodules('PIL')

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
# 程序化白名单过滤器
# 原理：扫描当前 Python 环境中所有可导入的顶级模块，
#       排除不在白名单中的模块，仅保留项目实际依赖。
# ============================================================

import os
import sys
import pkgutil

def _get_all_top_level_modules():
    """获取当前环境中所有可导入的顶级模块名称"""
    modules = set()
    # 内置模块（sys.builtin_module_names）
    modules.update(sys.builtin_module_names)
    # 已安装的包
    for pkg in pkgutil.iter_modules():
        modules.add(pkg.name)
    # 标准库（sys.stdlib_module_names，Python 3.10+）
    if hasattr(sys, 'stdlib_module_names'):
        modules.update(sys.stdlib_module_names)
    return modules

def _build_whitelist_excludes(whitelist, all_modules):
    """
    构建排除列表 = 所有模块 - 白名单模块。
    只排除第三方包，保留所有标准库和内置模块。
    """
    # 标准库和内置模块名（绝不应排除）
    stdlib = set(sys.builtin_module_names)
    if hasattr(sys, 'stdlib_module_names'):
        stdlib.update(sys.stdlib_module_names)

    # 只检查非标准库、非内置的第三方模块
    third_party = all_modules - stdlib

    # 将白名单中的模块名和它们的常见别名都加入保护
    protected = set(whitelist)

    # 排除 = 第三方模块 - 白名单
    to_exclude = sorted(third_party - protected)

    # 注意：PyInstaller 的 excludes 只对实际被扫描到的模块生效，
    # 不会影响未被 Analysis 依赖链引用的模块。
    return to_exclude


# ---- 白名单：项目实际依赖的 "Python 模块名"（非 PyPI 包名） ----
_MODULE_WHITELIST = [
    # ---- UI 框架 ----
    'PySide6', 'shiboken6',
    # ---- HTTP 网络 ----
    'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
    # ---- HTML/XML 解析 ----
    'bs4', 'soupsieve', 'lxml',
    # ---- Selenium 浏览器驱动 ----
    'selenium', 'trio', 'trio_websocket', 'outcome', 'sniffio',
    'wsproto', 'h11', 'websocket', 'sortedcontainers',
    # ---- UA 伪装 ----
    'fake_useragent',
    # ---- 图像处理 ----
    'PIL', 'numpy',
    # ---- 系统监控 ----
    'psutil',
    # ---- 文件导出 ----
    'openpyxl', 'docx', 'et_xmlfile',
    # ---- 类型注解支持（PySide6/docx/selenium 等多库依赖） ----
    'typing_extensions', 'typing_inspection',
    # ---- Windows 系统集成（psutil/selenium 依赖） ----
    'pywin32', 'win32com', 'pythonwin', 'win32', 'pywin32_system32',
    'ctypes', 'wmi',
    # ---- 加密/安全（pycryptodomex 依赖） ----
    'cffi', '_cffi_backend',
    # ---- 其他通用工具 ----
    'packaging',               # 版本号解析（多库依赖）
    'attr', 'attrs',           # 数据类工具
    # ---- 其他 ----
    'lz4', 'Cryptodome',       # selenium 内部 cookie 加密
    'dateutil',                # python-dateutil
    'yaml', '_yaml',
    'rpds',                    # jsonschema 依赖
    'markupsafe',              # jinja2 → selenium 依赖
    'pyexpat', 'elementtree',  # XML 解析
]

# 排除一切不在白名单中的第三方模块
_whitelist_excludes = _build_whitelist_excludes(
    _MODULE_WHITELIST,
    _get_all_top_level_modules(),
)

print(f"[spec] 白名单模块: {len(_MODULE_WHITELIST)} 个")
print(f"[spec] 将排除: {len(_whitelist_excludes)} 个无关第三方模块")

# ============================================================
# 输出路径：将最终打包产物从默认的 dist/ 改为 build/
# ============================================================
import PyInstaller.config
PyInstaller.config.CONF['distpath'] = 'build'
PyInstaller.config.CONF['workpath'] = 'build/_temp'

os.makedirs('build/_temp', exist_ok=True)

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
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
    ] + selenium_hidden + bs4_hidden + lxml_hidden + requests_hidden + urllib3_hidden + pil_hidden + docx_hidden + openpyxl_hidden + fake_ua_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_whitelist_excludes,
    noarchive=False,
    optimize=0,
)
# 主题文件（用 Tree + excludes 排除 __pycache__ 和 .pyc）
a.datas += Tree('src/ui/theme', prefix='ui/theme', excludes=['__pycache__', '*.pyc'])
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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='tour-crawler',
)