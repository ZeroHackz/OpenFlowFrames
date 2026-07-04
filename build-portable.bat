@echo off
cd /d "%~dp0OpenFlowFramesPy"
echo Building OpenFlowFrames portable executable...

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

REM Activate virtual environment
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies...
pip install --quiet customtkinter pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Building executable...
pyinstaller --noconfirm OpenFlowFramesPortable.spec
if %ERRORLEVEL% NEQ 0 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Copying runtime packages (ffmpeg + rife-ncnn-vulkan) next to the exe...
xcopy /E /I /Y /Q "..\Pkgs\av" "dist\Pkgs\av" >nul
xcopy /E /I /Y /Q "..\Pkgs\rife-ncnn" "dist\Pkgs\rife-ncnn" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Failed to copy runtime packages.
    pause
    exit /b 1
)

echo.
echo Build successful!
echo Portable app: dist\OpenFlowFramesPortable.exe (keep the Pkgs folder next to it)
echo.

call deactivate
pause
