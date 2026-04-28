@echo off
setlocal
cd /d "%~dp0\..\services\api"
set PYTHONPATH=%CD%
set KEY=%1
if "%KEY%"=="" set KEY=clemastine
python -c "import asyncio; from app.scheduler import run_one_intervention; from app.ontology import INTERVENTIONS_BY_KEY; asyncio.run(run_one_intervention(INTERVENTIONS_BY_KEY['%KEY%']))"
endlocal
