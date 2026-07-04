# -*- mode: python ; coding: utf-8 -*-
import os

root = os.path.dirname(SPECPATH)  # repo root (spec lives in portable/)

a = Analysis(
    [os.path.join(SPECPATH, 'launch.py')],
    pathex=[root, os.path.join(root, 'venv', 'Lib', 'site-packages')],
    binaries=[],
    datas=[(os.path.join(root, 'venv', 'Lib', 'site-packages', 'customtkinter'), 'customtkinter')],
    hiddenimports=['customtkinter'],
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
    a.binaries,
    a.datas,
    [],
    name='OpenFlowFramesPortable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
