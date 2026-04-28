@echo off
setlocal
cd /d "%~dp0\.."
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERR] Python not found on PATH.
    echo       Install Python 3.11+ from https://www.python.org/downloads/
    echo       Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
python scripts\init.py %*
endlocal
