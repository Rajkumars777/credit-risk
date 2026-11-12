# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

model_path = PROJECT_ROOT / "src" / "backend" / "models" / "May 12 Status Contracts_Extracted New_lgbm.joblib"
datas = [
    (str(PROJECT_ROOT / "src"), "src/"),
    (str(PROJECT_ROOT / "src" / "data" / "img"), "img/"),
]
if model_path.exists():
    datas.append((str(model_path), "src/backend/models/"))

icon_path = PROJECT_ROOT / "ltid_logo.ico"
icons = [str(icon_path)] if icon_path.exists() else []

a = Analysis(
    [str(PROJECT_ROOT / "src" / "frontend" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name="JACCSScore",
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
    icon=icons,
)
