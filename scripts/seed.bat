@echo off
setlocal
cd /d "%~dp0\..\services\api"
set PYTHONPATH=%CD%
python -m app.seed.extractor
endlocal
