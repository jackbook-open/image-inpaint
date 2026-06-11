# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path
import sys


block_cipher = None
project_root = Path(SPECPATH).parent
src_root = project_root / "src"
macos_entitlements = project_root / "packaging" / "macos-entitlements.plist"

hiddenimports = collect_submodules("PIL") + [
    "tkinter",
    "yaml",
    "md_image_inpaint.desktop_app",
]

a = Analysis(
    [str(src_root / "md_image_inpaint" / "desktop_app.py")],
    pathex=[str(project_root), str(src_root)],
    binaries=[],
    datas=[
        (str(project_root / "README.md"), "."),
        (str(project_root / "LICENSE"), "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageInpaint",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(macos_entitlements) if sys.platform == "darwin" else None,
)

smoke_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageInpaintSmoke",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(macos_entitlements) if sys.platform == "darwin" else None,
)

coll = COLLECT(
    exe,
    smoke_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ImageInpaint",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ImageInpaint.app",
        icon=None,
        bundle_identifier="org.image-inpaint.desktop",
        info_plist={
            "CFBundleName": "Image Inpaint",
            "CFBundleDisplayName": "Image Inpaint",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHumanReadableCopyright": "MIT",
        },
    )
