# -*- mode: python ; coding: utf-8 -*-
"""فایل مشخصات PyInstaller برای ساخت اجرایی ویندوزی «مشاور هوشمند کنکور».

هدف: تولید یک پوشهٔ توزیع (one-folder) که در ویندوز ۱۰/۱۱ بدون نصب پایتون
اجرا می‌شود. ساخت تک‌فایل (--onefile) به‌دلیل زمان استخراج و مسائل آنتی‌ویروس
پیشنهاد نمی‌شود؛ به‌جای آن یک نصب‌کنندهٔ Inno Setup (اختیاری) ساخته می‌شود.

اجرا:
    pyinstaller k2.spec --noconfirm

خروجی:
    packaging/output/K2/‌K2.exe
"""

from pathlib import Path

PROJECT_ROOT = Path(SPEC).resolve().parent  # noqa: F821  → مسیر پوشهٔ spec
SRC = PROJECT_ROOT / "src"
ASSETS = SRC / "k2" / "ui" / "assets"

# --- داده‌های ثابت همراه برنامه ---
datas = [
    (str(ASSETS / "fonts"), "k2/ui/assets/fonts"),
]

# --- قلاب‌های لازم برای PySide6 ---
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "jdatetime",
    "sqlite3",
]

# --- کتابخانه‌هایی که نباید جمع شوند (کاهش حجم و رفع خطای جمع) ---
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.Qt3DCore",
    "PySide6.QtMultimedia",
    "PySide6.QtBluetooth",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtNetworkAuth",
    "PySide6.QtPdf",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtTest",
    "PySide6.QtSql",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtSpatialAudio",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
]


a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "k2_launcher.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="K2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # پنجرهٔ گرافیکی؛ خروجی خطا در فایل log نوشته می‌شود
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS / "k2.ico") if (ASSETS / "k2.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="K2",
)
