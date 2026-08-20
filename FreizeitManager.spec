# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-onedir-Spec fuer den FreizeitManager.

Lokal und in der Pipeline:

    python -m PyInstaller FreizeitManager.spec --noconfirm --clean

Ergebnis:
    dist/FreizeitManager/FreizeitManager        (Linux)
    dist/FreizeitManager/FreizeitManager.exe    (Windows)

Die Pfade muessen zu ``linux_executable`` / ``windows_executable`` in
module.json passen, sonst lehnt der Paketierer den Build ab.

Nutzerdaten liegen bewusst ausserhalb des Programmordners. Portable Starts
setzen FREIZEITMANAGER_DATA_DIR bzw. legen portable.flag daneben.
"""

from pathlib import Path

ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "version.json"), "."),
    (str(ROOT / "module.json"), "."),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "CHANGELOG.md"), "."),
]

hiddenimports = [
    "sqlalchemy.dialects.sqlite",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Reine Python-Ausschluesse. Qt-Bibliotheken nachtraeglich aus
    # ``a.binaries`` zu streichen wurde bewusst wieder verworfen: PyInstaller
    # legt fuer verschobene Bibliotheken Symlinks an, die dabei ins Leere
    # zeigen. Die Anwendung startete trotzdem, weil sie diese Bibliotheken nie
    # laedt - der Defekt fiel erst beim Packen auf. Ein um 15 Prozent
    # kleineres, aber innerlich kaputtes Paket ist kein guter Tausch.
    excludes=[
        "tkinter", "unittest", "pydoc", "doctest", "pytest",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
        "PySide6.QtQuickControls2", "PySide6.QtQuick3D",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DExtras",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
        "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtTest",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets", "PySide6.QtSpatialAudio",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FreizeitManager",
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FreizeitManager",
)
