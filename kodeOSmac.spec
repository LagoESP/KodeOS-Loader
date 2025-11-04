# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# 1. datos de esptool ─ stub JSON + .stub
esptool_datas = collect_data_files('esptool', includes=['targets/**/*'])

block_cipher = None

a = Analysis(
    ['kodeOS.py'],
    pathex=['.'],                    # <─ aquí el cambio
    binaries=[],
    datas=[('images', 'images')] + esptool_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='kodeOS',
    console=False,
    icon='icon.ico',
    upx=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='kodeOS',
)

app = BUNDLE(
    coll,
    name='kodeOS.app',
    icon='icon.ico',
)
