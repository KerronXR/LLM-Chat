@echo off
title Local AI Assistant
echo Checking dependencies...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=".venv\Scripts\python.exe"
) else if exist "..\LLM\.venv\Scripts\python.exe" (
    set PYTHON_EXE="..\LLM\.venv\Scripts\python.exe"
)

echo Initializing Local AI Environment...
%PYTHON_EXE% "run_ui.py"
if %errorlevel% neq 0 (
    echo Error: Server failed to start.
    pause
)
