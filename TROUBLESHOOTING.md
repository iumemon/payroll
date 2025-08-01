# 🔧 Troubleshooting Guide - Payroll Management System

## Terminal Command Issues

### Problem 1: Commands Not Responding / Hanging

**Symptoms:**
- Terminal freezes after running a command
- Commands take unusually long to execute
- No output or response from terminal

**Solutions:**

1. **Kill Stuck Processes:**
```powershell
# PowerShell
Get-Process python | Stop-Process -Force
Get-Process uvicorn | Stop-Process -Force

# Command Prompt
taskkill /f /im python.exe
taskkill /f /im uvicorn.exe
```

2. **Restart Terminal:**
- Close and reopen your terminal window
- Or press `Ctrl+C` to interrupt the current command

3. **Check for Background Processes:**
```powershell
# Check what's running on port 8000
netstat -ano | findstr :8000

# Kill specific process by PID
Stop-Process -Id [PID] -Force
```

### Problem 2: PowerShell Command Separator Issues

**Problem:** `&&` doesn't work in PowerShell

**Solution:** Use proper PowerShell syntax:
```powershell
# ❌ Wrong
cd /path && python script.py

# ✅ Correct
cd C:\path; python script.py
# OR
cd C:\path
python script.py
```

### Problem 3: Path Issues

**Problem:** Path not recognized or contains special characters

**Solutions:**
```powershell
# Use proper Windows paths
cd "G:\Payrol"  # Use quotes for paths with spaces
Set-Location "G:\Payrol"  # PowerShell preferred method

# Avoid using forward slashes in Windows
# ❌ cd /g%3A/Payrol
# ✅ cd G:\Payrol
```

## FastAPI Server Issues

### Problem 1: "No module named uvicorn"

**Solution:**
```bash
pip install uvicorn
# OR install all requirements
pip install -r requirements.txt
```

### Problem 2: Port Already in Use

**Symptoms:** `Address already in use` error

**Solutions:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID [PID] /F

# Or use a different port
python -m uvicorn app.main:app --reload --port 8001
```

### Problem 3: Import Errors

**Symptoms:** `ModuleNotFoundError` or `ImportError`

**Solutions:**
1. **Install missing packages:**
```bash
pip install -r requirements.txt
```

2. **Check virtual environment:**
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1  # PowerShell
# OR
.\venv\Scripts\activate.bat  # Command Prompt
```

3. **Verify Python path:**
```bash
python -c "import sys; print(sys.path)"
```

## Database Issues

### Problem 1: Database File Locked

**Symptoms:** `database is locked` error

**Solutions:**
```powershell
# Stop all Python processes
Get-Process python | Stop-Process -Force

# Delete lock file if exists
Remove-Item "payroll.db-wal" -Force -ErrorAction SilentlyContinue
Remove-Item "payroll.db-shm" -Force -ErrorAction SilentlyContinue

# Restart server
python -m uvicorn app.main:app --reload
```

### Problem 2: Table Creation Errors

**Solution:** Delete and recreate database:
```powershell
# Stop server first
# Delete database file
Remove-Item "payroll.db" -Force

# Restart server (tables will be recreated)
python -m uvicorn app.main:app --reload
```

## Performance Issues

### Problem 1: Slow Response Times

**Solutions:**
1. **Check system resources:**
```powershell
# Check CPU and memory usage
Get-Process python | Select-Object CPU, WorkingSet, ProcessName
```

2. **Reduce auto-reload frequency:**
```bash
# Use less aggressive reloading
python -m uvicorn app.main:app --reload --reload-delay 2
```

3. **Use production settings:**
```bash
# For testing performance
python -m uvicorn app.main:app --workers 1
```

## Quick Start Scripts

### Easy Server Startup

**PowerShell Users:**
```powershell
# Run the startup script
.\start.ps1
```

**Command Prompt Users:**
```cmd
# Run the startup script
start.bat
```

**Manual Start:**
```bash
# Basic manual start
cd G:\Payrol
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Common Environment Issues

### Problem 1: Virtual Environment Issues

**Create new virtual environment:**
```powershell
# Create new venv
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### Problem 2: Python Version Issues

**Check Python version:**
```bash
python --version
# Should be Python 3.11 or higher
```

**Install correct Python version if needed:**
- Download from [python.org](https://python.org)
- Make sure to add to PATH during installation

## Testing Connectivity

### Verify Server is Running

1. **Check process:**
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

2. **Test endpoints:**
```powershell
# Using PowerShell (if available)
Invoke-WebRequest http://localhost:8000/

# Using curl (if available)
curl http://localhost:8000/

# Or open in browser
start http://localhost:8000/api/docs
```

3. **Check logs:**
- Look at terminal output for errors
- Check for database connection messages
- Verify all imports are successful

## Emergency Recovery

### Nuclear Option - Complete Reset

If nothing else works:

1. **Stop all processes:**
```powershell
Get-Process python | Stop-Process -Force
```

2. **Clean up files:**
```powershell
Remove-Item "payroll.db*" -Force
Remove-Item "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
```

3. **Reinstall environment:**
```powershell
Remove-Item "venv" -Recurse -Force
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. **Restart server:**
```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Getting Help

### Diagnostic Information

When reporting issues, include:

1. **System info:**
```powershell
python --version
pip list | findstr -i "fastapi uvicorn sqlalchemy"
```

2. **Error messages:**
- Copy the full error traceback
- Include terminal output

3. **Environment:**
- Operating system version
- Terminal type (PowerShell, Command Prompt, etc.)
- Virtual environment status

### Useful Commands for Debugging

```powershell
# Check Python packages
pip list

# Check environment variables
Get-ChildItem Env:

# Check file permissions
Get-Acl "payroll.db"

# Test database connection
python -c "from app.core.database import sync_engine; print('DB OK')"

# Test imports
python -c "from app.main import app; print('Imports OK')"
```

---

## Quick Reference

**Start Server:** `.\start.ps1` or `start.bat`
**Stop Server:** `Ctrl+C`
**Kill Stuck Process:** `Get-Process python | Stop-Process -Force`
**Check Port:** `netstat -ano | findstr :8000`
**API Docs:** `http://localhost:8000/api/docs`

**Emergency Reset:**
1. Stop all Python processes
2. Delete `payroll.db`
3. Restart server 