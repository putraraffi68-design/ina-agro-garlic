@echo off
REM Menjalankan INA Agro-GARLIC di http://localhost:8000
cd /d "%~dp0app"
python -m uvicorn main:app --reload --port 8000
