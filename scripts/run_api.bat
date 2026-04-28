@echo off
setlocal
cd /d "%~dp0\..\services\api"
set PYTHONPATH=%CD%
if "%NEUROFORGE_SCHEDULER%"=="" set NEUROFORGE_SCHEDULER=1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8077 --reload
endlocal
