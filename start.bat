@echo off
REM Payroll Management System - Development Server Startup Script (Command Prompt)

echo 🚀 Starting Payroll Management System...

REM Check if we're in the right directory
if not exist "app\main.py" (
    echo ❌ Error: Not in the correct directory. Please run this script from the project root.
    echo Current directory: %CD%
    echo Expected files: app\main.py
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python not found. Please install Python or check your PATH.
    pause
    exit /b 1
)

python --version
echo ✅ Python found

REM Check if virtual environment exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  Warning: Virtual environment not found. Using system Python.
)

REM Check if required packages are installed
python -c "import fastapi, uvicorn, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Warning: Some packages may be missing. Installing requirements...
    pip install -r requirements.txt
) else (
    echo ✅ Required packages found
)

REM Kill any existing server on port 8000
echo 🔧 Checking for existing server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Stopping existing server process %%a...
    taskkill /PID %%a /F >nul 2>&1
)

REM Start the development server
echo.
echo 🌐 Starting FastAPI development server...
echo 📍 Server will be available at:
echo    - API Docs: http://localhost:8000/api/docs
echo    - Health Check: http://localhost:8000/
echo    - Payroll API: http://localhost:8000/api/v1/payroll/
echo.
echo Press Ctrl+C to stop the server
echo ================================

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo ❌ Error starting server
    echo 💡 Try running: pip install -r requirements.txt
    pause
)

pause 