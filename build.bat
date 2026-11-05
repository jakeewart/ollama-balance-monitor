@echo off

set PYTHON_CMD=python

where python >nul 2>nul
if %errorlevel% neq 0 (
    where python3 >nul 2>nul
    if %errorlevel% neq 0 (
        echo Error: Python is not installed or not in PATH.
        echo Please install Python from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
)

echo Setting Ollama API key...
powershell -ExecutionPolicy Bypass -File "%~dp0src\set-api-key.ps1" -Silent
if %errorlevel% neq 0 (
    echo API key setup cancelled or failed.
    pause
    exit /b 1
)

%PYTHON_CMD% --version
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r "%~dp0src\requirements.txt"

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q src\ollama-balance-monitor.spec 2>nul

%PYTHON_CMD% -m PyInstaller --onefile --noconsole --icon="%~dp0assets\ollama.ico" --add-data "%~dp0assets\ollama.ico;assets" --name ollama-balance-monitor --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0src" "%~dp0src\main.py"
pause

