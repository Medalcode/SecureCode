@echo off
title SecureCode - Servicios Locales
cd /d "%~dp0"
echo ============================================================
echo   Iniciando SecureCode Backend (FastAPI) y Frontend (Vite)
echo ============================================================
echo.

start "SecureCode FastAPI Backend (Puerto 8000)" cmd /k "python scripts/start_backend.py"
start "SecureCode Vite Frontend (Puerto 5173)" cmd /k "cd frontend && npm run dev"

echo Servicios lanzados en ventanas independientes.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo ============================================================
pause
