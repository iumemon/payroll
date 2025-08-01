# Simple Payroll Management System Startup Script
# No Unicode characters to avoid PowerShell encoding issues

Write-Host "Starting Payroll Management System..." -ForegroundColor Green

# Check if we're in the right directory
if (!(Test-Path "app\main.py")) {
    Write-Host "ERROR: Not in project root directory" -ForegroundColor Red
    Write-Host "Current: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Activate virtual environment if available
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
}

# Install packages if needed
try {
    python -c "import fastapi, uvicorn, sqlalchemy" 2>$null
    Write-Host "Required packages found" -ForegroundColor Green
} catch {
    Write-Host "Installing requirements..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Kill existing server
$process = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "Stopping existing server..." -ForegroundColor Yellow
    Stop-Process -Id $process.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start server
Write-Host ""
Write-Host "Starting development server..." -ForegroundColor Green
Write-Host "Available at: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "========================" -ForegroundColor Green

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 