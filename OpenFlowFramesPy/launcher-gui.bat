@echo off
cd /d "%~dp0"
echo OpenFlowFrames Launcher

REM Create virtual environment if missing
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment. Is Python installed and on PATH?
        pause
        exit /b 1
    )
)

REM Install dependencies if missing
venv\Scripts\python.exe -c "import customtkinter" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing dependencies...
    venv\Scripts\python.exe -m pip install --quiet customtkinter
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Launching GUI...
start "" venv\Scripts\pythonw.exe launch.py
exit /b 0
