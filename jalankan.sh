#!/usr/bin/env bash
# Menjalankan INA Agro-GARLIC di http://localhost:8000
cd "$(dirname "$0")/app" && python -m uvicorn main:app --reload --port 8000
