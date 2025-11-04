# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

esptool_datas = collect_data_files('esptool', includes=['targets/**/*'])

a = Analysis(
    ['kodeOS.py'],
    pathex=['.'],
    binaries=[],
    datas=[('images', 'images')] + esptool_datas,
)

pyz = PYZ(a.pure, a.zipped_data)

# ---- fase intermedia: EXE sin bins -----------------------------------------
exe_stage = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='kodeOS',
    icon='icon.ico',
    console=False,
)

# ---- empaquetado en un único archivo ---------------------------------------
pkg = PKG(
    exe_stage,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='kodeOS.pkg',
)

exe = EXE(
    pkg,
    name='kodeOS.exe',      # ← este es el binario final
    icon='icon.ico',
    console=False,
    append_pkg=False,
)
