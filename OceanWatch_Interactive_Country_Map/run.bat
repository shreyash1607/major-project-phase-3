@echo off
REM One-click launcher (Windows): creates .venv, installs deps, starts server, opens browser
cd /d "%~dp0backend"
if not exist "..\.venv\Scripts\python.exe" (py -3 -m venv ..\.venv || python -m venv ..\.venv)
"..\.venv\Scripts\python.exe" -m pip install -q -r requirements.txt
start "" http://localhost:8000
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
pause
