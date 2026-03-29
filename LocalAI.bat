@echo off
title Local AI Assistant
echo Checking dependencies...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

echo Initializing Local AI Environment...
".\.venv\Scripts\python.exe" "C:\Users\roman\OneDrive\Documents\Code\LLM\run_ui.py"
if %errorlevel% neq 0 (
    echo Error: Server failed to start.
    pause
)
