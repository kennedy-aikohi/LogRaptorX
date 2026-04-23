@echo off
title LogRaptorX Build

echo.
echo  ============================================================
echo   LogRaptorX v1.0.0 - Windows Build
echo   Developer : Kennedy Aikohi
echo   GitHub    : github.com/kennedy-aikohi
echo   LinkedIn  : linkedin.com/in/aikohikennedy
echo  ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] %PYVER%

echo.
echo  [1/4] Installing dependencies...
python -m pip install PyQt6 pyinstaller python-evtx --quiet --disable-pip-version-check
if errorlevel 1 (
    echo  [ERROR] pip install failed.
    pause
    exit /b 1
)
echo  [OK] Dependencies ready.

echo.
echo  [2/4] Cleaning previous build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo  [OK] Clean done.

echo.
echo  [3/4] Building EXE - please wait up to 3 minutes...
python -m PyInstaller --noconfirm --clean --log-level WARN --noupx ^
    --onefile ^
    --windowed ^
    --name LogRaptorX ^
    --paths src ^
    --hidden-import Evtx ^
    --hidden-import Evtx.Evtx ^
    --hidden-import Evtx.Views ^
    --hidden-import Evtx.BinaryParser ^
    --hidden-import Evtx.Nodes ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import xml.etree.ElementTree ^
    src/main.py
if errorlevel 1 (
    echo.
    echo  [ERROR] Build failed. See output above.
    pause
    exit /b 1
)
echo  [OK] Build complete.

echo.
echo  [4/4] Verifying...
if not exist dist\LogRaptorX.exe (
    echo  [ERROR] dist\LogRaptorX.exe not found.
    pause
    exit /b 1
)

for %%F in (dist\LogRaptorX.exe) do set SIZE=%%~zF
set /a SIZEMB=%SIZE% / 1048576
echo  [OK] dist\LogRaptorX.exe is %SIZEMB% MB

echo.
echo  ============================================================
echo   BUILD SUCCESSFUL  -  dist\LogRaptorX.exe is ready
echo  ============================================================
echo.
pause
