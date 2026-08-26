@echo off
title IT-RECOMMEND System Launcher
echo ===================================================
echo   Starting IT-RECOMMEND Backend and Frontend...
echo ===================================================

:: 1. Start Backend in a new window
start "IT-RECOMMEND Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && "%~dp0venv\Scripts\uvicorn.exe" shop_api:app --reload --port 3000 --host 0.0.0.0"

:: 2. Start Frontend
cd /d "%~dp0It-shop"
npx ng serve --port 4200 --open
