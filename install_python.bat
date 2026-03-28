@echo off
setlocal

echo Installing Python using winget...
winget install Python.Python.3
if errorlevel 1 (
    echo.
    echo Installation may have failed or Python is already installed.
    echo If Python was just installed, please close this window and run 'run.bat'.
    pause
    exit /b 1
)

echo.
echo Python installation complete!
echo Please close this window and run 'run.bat' to start the app.
pause
