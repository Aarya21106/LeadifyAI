@echo off
echo 🚀 Starting Leadify AI FAST DEMO...
cd /d "%~dp0"

echo 🛠️ Running Setup (Resetting DB)...
".\.venv\Scripts\python.exe" setup_demo.py

echo 🔥 Starting Backend + Frontend...
".\.venv\Scripts\python.exe" -m uvicorn leadify.api.main:app --host 127.0.0.1 --port 8000
pause
