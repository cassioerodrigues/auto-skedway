@echo off
REM Start Frontend Dashboard Server
REM This script starts the Flask API server for the Execution Dashboard

echo.
echo ╔════════════════════════════════════════╗
echo ║   Execution Dashboard - Frontend API   ║
echo ╚════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  Flask is not installed. Installing dependencies...
    pip install -r ../requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

echo ✅ All dependencies are installed
echo.
echo 🚀 Starting Frontend Dashboard...
echo.
echo 📍 Server will be available at: http://localhost:5000
echo.
echo 🛑 Press Ctrl+C to stop the server
echo.

python api.py

pause
