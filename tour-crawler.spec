# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 自动收集 selenium 所有子模块（解决 importlib 动态导入问题）
selenium_hidden = collect_submodules('selenium')
# 自动收集 selenium 数据文件（包含 selenium-manager.exe 浏览器驱动管理器）
selenium_datas = collect_data_files('selenium')
# 自动收集 bs4 所有子模块（beautifulsoup4 → bs4）
bs4_hidden = collect_submodules('bs4')
# 自动收集 fake_useragent 数据文件（UA 数据库）
fake_ua_datas = collect_data_files('fake_useragent')
# 收集 certifi SSL 证书文件（requests HTTPS 必需）
certifi_datas = collect_data_files('certifi')

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/ui/resources', 'ui/resources'),
        ('src/ui/theme', 'ui/theme'),
        ('src/assets', 'assets'),
    ] + selenium_datas + fake_ua_datas + certifi_datas,
    hiddenimports=[
        # PySide6
        'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtMultimedia',
        # HTTP and parsing
        'requests', 'urllib3', 'certifi',
        'lxml', 'openpyxl', 'docx',
        # browser_cookie3 (用于读取浏览器本地 Cookie)
        'browser_cookie3',
    ] + selenium_hidden + bs4_hidden,
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
