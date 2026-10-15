@echo off
setlocal
cd /d "%~dp0"
REM ------------------------------------------------------------------
REM  1) installs build deps  2) builds dist\ERP\ERP.exe (one-dir)
REM  3) if Inno Setup 6 is installed -> also builds installer\ERP_Setup.exe
REM ------------------------------------------------------------------

py -m pip install -r requirements.txt pyinstaller pillow
if errorlevel 1 goto :error

REM regenerate the per-theme icons
py tools\make_icons.py
if errorlevel 1 goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

py -m PyInstaller --noconfirm --clean main.spec
if errorlevel 1 goto :error

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
    "%ISCC%" installer.iss
    if errorlevel 1 goto :error
    echo Installer: installer\ERP_Setup.exe
) else (
    echo Inno Setup not found - skipping installer. You can zip dist\ERP instead.
)

echo.
echo Build finished: dist\ERP\ERP.exe
pause
exit /b 0

:error
echo Build failed. Review the error output above.
pause
exit /b 1
