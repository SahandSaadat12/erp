# -*- mode: python ; coding: utf-8 -*-
# ONE-DIR build (folder).  Much more stable than --onefile:
#   * no %TEMP%\_MEIxxxx extraction  -> no "Failed to remove temporary directory"
#   * theme change / restart works, antivirus does not lock the temp folder
#   * starts faster
# Output: dist\ERP\ERP.exe   (the whole dist\ERP folder is what you ship)
from PyInstaller.utils.hooks import collect_all, collect_submodules

ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")
per_datas, per_binaries, per_hidden = collect_all("persiantools")
xls_datas, xls_binaries, xls_hidden = collect_all("xlsxwriter")

project_modules = []
for pkg in ("ui", "db", "utils", "licensing"):
    project_modules += collect_submodules(pkg)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=ctk_binaries + per_binaries + xls_binaries,
    datas=ctk_datas + per_datas + xls_datas + [("icons", "icons")],
    hiddenimports=(
        ctk_hidden + per_hidden + xls_hidden + project_modules
        + ["PIL._tkinter_finder", "PIL.ImageTk", "numpy",
           "config", "paths", "style", "themes", "database", "security"]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pandas", "scipy", "IPython", "pytest",
              "notebook", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ERP",
    icon="icons/app.ico",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ERP",
)
