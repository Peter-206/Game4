@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Follow the setup steps in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
pause
