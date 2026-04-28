@echo off
setlocal
cd /d "%~dp0\..\web"
if not exist node_modules (
    call npm install --no-audit --no-fund
)
call npm run dev
endlocal
