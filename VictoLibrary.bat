@echo off
REM Change to this file's directory
cd /d "%~dp0"

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Run the launcher script silently
pythonw run_desktop.py
