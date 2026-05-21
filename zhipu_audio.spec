# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

# 获取当前脚本所在目录（兼容PyInstaller执行环境）
try:
    spec_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    spec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

a = Analysis(
    ['app.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        # voices.db 不在打包范围内，由应用运行时自动创建
    ],
    hiddenimports=[
        'flask',
        'requests',
        'sqlite3',
        'uuid',
        'threading',
        'queue',
        'webbrowser',
        'json',
        'time',
        'subprocess',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows 配置
if sys.platform == 'win32':
    # 设置图标（如果存在）
    icon_path = os.path.join(spec_dir, 'app.ico')
    icon_param = icon_path if os.path.exists(icon_path) else None
    
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ZhipuAudio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,  # 保留控制台输出
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_param  # 图标文件可选
    )
else:
    # Mac 配置
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='ZhipuAudio',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,  # 保留控制台输出
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='ZhipuAudio',
    )

    app = BUNDLE(
        coll,
        name='ZhipuAudio.app',
        icon=None,  # 使用系统默认图标
        bundle_identifier='com.zhipu.audio',
        version='1.0.0',
    )
