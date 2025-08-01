# Payroll Management System - Development Server Startup Script

Write-Host "Starting Payroll Management System..." -ForegroundColor Green

# Check if we're in the right directory
if (!(Test-Path "app\main.py")) {
    Write-Host "Error: Not in the correct directory. Please run this script from the project root." -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "Expected files: app\main.py" -ForegroundColor Yellow
    exit 1
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python not found. Please install Python or check your PATH." -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists and activate it
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Warning: Virtual environment not found. Using system Python." -ForegroundColor Yellow
}

# Check if required packages are installed
try {
    python -c "import fastapi, uvicorn, sqlalchemy" 2>$null
    Write-Host "Required packages found" -ForegroundColor Green
} catch {
    Write-Host "Warning: Some packages may be missing. Installing requirements..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Kill any existing server on port 8000
$existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "Stopping existing server on port 8000..." -ForegroundColor Yellow
    Stop-Process -Id $existingProcess.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start the development server
Write-Host "Starting FastAPI development server..." -ForegroundColor Green
Write-Host "Server will be available at:" -ForegroundColor Cyan
Write-Host "   - API Docs: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "   - Health Check: http://localhost:8000/" -ForegroundColor Cyan
Write-Host "   - Payroll API: http://localhost:8000/api/v1/payroll/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Green

try {
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} catch {
    Write-Host "Error starting server: $_" -ForegroundColor Red
    Write-Host "Try running: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
} 