# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('src/ui/resources', 'ui/resources'), ('src/ui/theme', 'ui/theme'), ('src/assets', 'assets')],
    hiddenimports=['PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtMultimedia', 'browser_cookie3', 'fake_useragent', 'requests', 'beautifulsoup4', 'lxml', 'openpyxl', 'docx'],
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
