#!/usr/bin/env bash
# One-click launcher (Mac/Linux): creates .venv, installs deps, starts server
set -e; cd "$(dirname "$0")/backend"
[ -d ../.venv ] || python3 -m venv ../.venv
../.venv/bin/python -m pip install -q -r requirements.txt
(sleep 2; command -v xdg-open >/dev/null && xdg-open http://localhost:8000 || open http://localhost:8000) >/dev/null 2>&1 &
../.venv/bin/python -m uvicorn app.main:app --port 8000
