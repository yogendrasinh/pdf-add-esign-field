@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\
set APP_NAME=pdf-add-esign-field
set ENTRY_POINT=%PROJECT_ROOT%source\app.py
set VENV_PYTHON=%PROJECT_ROOT%.venv\Scripts\python.exe
set VENV_PIP=%PROJECT_ROOT%.venv\Scripts\pip.exe
set ICON_PATH=%SCRIPT_DIR%%APP_NAME%.ico

set /p VERSION=<%SCRIPT_DIR%version.txt
set VERSION=%VERSION: =%

echo [build] App:     %APP_NAME%
echo [build] Version: %VERSION%
echo [build] Entry:   %ENTRY_POINT%
echo [build] Icon:    %ICON_PATH%

if not exist "%ICON_PATH%" (
    echo ERROR: Icon file not found: %ICON_PATH%
    pause & exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo ERROR: .venv not found. Run run.bat first to create the virtual environment.
    pause & exit /b 1
)

echo [build] Checking PyInstaller...
"%VENV_PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [build] Installing PyInstaller...
    "%VENV_PIP%" install pyinstaller || (echo ERROR: pip install failed. & pause & exit /b 1)
)

echo [build] Locating tkinterdnd2...
"%VENV_PYTHON%" -c "import tkinterdnd2, os; print(os.path.dirname(tkinterdnd2.__file__))" > "%TEMP%\tkdnd_path.txt"
set /p TKDND_PKG=<"%TEMP%\tkdnd_path.txt"
del "%TEMP%\tkdnd_path.txt"
if "%TKDND_PKG%"=="" (echo ERROR: Cannot locate tkinterdnd2. & pause & exit /b 1)
set TKDND_SOURCE=%TKDND_PKG%\tkdnd
echo [build] tkdnd: %TKDND_SOURCE%

cd /d "%SCRIPT_DIR%"

"%VENV_PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "%APP_NAME%" ^
    --icon "%ICON_PATH%" ^
    --add-data "%TKDND_SOURCE%;tkinterdnd2/tkdnd" ^
    --collect-all pyhanko ^
    --collect-all pyhanko_certvalidator ^
    --collect-all pymupdf ^
    --hidden-import fitz ^
    --hidden-import PIL._tkinter_finder ^
    --exclude-module unittest ^
    --exclude-module doctest ^
    --exclude-module pdb ^
    --exclude-module difflib ^
    --exclude-module ftplib ^
    --exclude-module imaplib ^
    --exclude-module poplib ^
    --exclude-module smtplib ^
    --exclude-module smtpd ^
    --exclude-module telnetlib ^
    --exclude-module xmlrpc ^
    --exclude-module turtle ^
    --exclude-module tkinter.test ^
    --exclude-module test ^
    "%ENTRY_POINT%"

if errorlevel 1 (echo ERROR: PyInstaller failed. & pause & exit /b 1)

set DIST_DIR=%SCRIPT_DIR%dist\%APP_NAME%
set ZIP_NAME=%APP_NAME%_windows_v%VERSION%.zip
set ZIP_PATH=%SCRIPT_DIR%%ZIP_NAME%

echo [build] Waiting for file handles to release...
timeout /t 5 /nobreak >nul

echo [build] Creating %ZIP_NAME%...
powershell -Command "try { Compress-Archive -Path '%DIST_DIR%' -DestinationPath '%ZIP_PATH%' -Force; exit 0 } catch { Write-Error $_; exit 1 }"
if errorlevel 1 (echo ERROR: Zip failed. & pause & exit /b 1)

echo.
echo [build] SUCCESS: %ZIP_PATH%
echo.
pause
