@echo off
setlocal

:: Check if Python is installed
where python >nul 2>&1
if errorlevel 1 (
    echo Python is not installed on this system.
    echo Please run 'install_python.bat' to install Python, then run this script again.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist ".venv\" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Install dependencies
echo Installing dependencies...
pip install -r source\requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

:: Run the app
echo Starting app...
python source\app.py

endlocal
