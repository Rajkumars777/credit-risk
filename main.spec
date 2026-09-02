# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\LTID\\credit-scoring-app\\src\\frontend\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\LTID\\credit-scoring-app\\src', 'src/'), ('D:\\LTID\\credit-scoring-app\\src\\backend\\models\\May 12 Status Contracts_Extracted New_lgbm.joblib', 'src/backend/models/')],
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
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\LTID\\credit-scoring-app\\ltid_logo(1).ico'],
)
