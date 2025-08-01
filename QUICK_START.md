# 🚀 Quick Start Guide - Payroll Management System

## Essential Commands

### Start Development Server
```powershell
# PowerShell (recommended - no Unicode issues)
.\start_simple.ps1

# Command Prompt
start.bat

# Manual (if scripts fail)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Stop Server
```
Ctrl+C (in terminal where server is running)
```

### Emergency Stop
```powershell
Get-Process python | Stop-Process -Force
```

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| **`&&` not working** | Use `;` in PowerShell or separate commands |
| **Path not found** | Use `G:\Payrol` not `/g%3A/Payrol` |
| **Module not found** | Run `pip install -r requirements.txt` |
| **Port in use** | `netstat -ano \| findstr :8000` then kill process |
| **Terminal hanging** | Press `Ctrl+C` and restart |
| **Import errors** | Check virtual environment is activated |

## PowerShell Best Practices

```powershell
# ✅ Correct syntax
cd G:\Payrol; python script.py
Set-Location "G:\Payrol"

# ❌ Avoid these
cd /g%3A/Payrol && python script.py
```

## Development Workflow

1. **Check Environment**:
   ```powershell
   python --version
   pip list | findstr -i "fastapi uvicorn"
   ```

2. **Start Server**:
   ```powershell
   .\start_simple.ps1
   ```

3. **Test System**:
   - API Docs: http://localhost:8000/api/docs
   - Health Check: http://localhost:8000/

4. **Stop Server**:
   ```
   Ctrl+C
   ```

## Key URLs

- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/
- **Payroll Endpoints**: http://localhost:8000/api/v1/payroll/
- **Employee Endpoints**: http://localhost:8000/api/v1/employees/
- **Auth Endpoints**: http://localhost:8000/api/v1/auth/

## File Structure

```
Payrol/
├── start_simple.ps1     # PowerShell startup (no Unicode)
├── start.bat           # Command Prompt startup
├── TROUBLESHOOTING.md  # Complete troubleshooting guide
├── app/
│   ├── main.py         # FastAPI application
│   ├── api/v1/         # API endpoints
│   ├── models/         # Database models
│   ├── services/       # Business logic
│   └── schemas/        # Pydantic schemas
└── requirements.txt    # Python dependencies
```

## Testing Commands

```powershell
# Test imports
python -c "from app.main import app; print('Imports OK')"

# Test database
python -c "from app.core.database import sync_engine; print('DB OK')"

# Check packages
pip list | findstr -i "fastapi uvicorn sqlalchemy"

# Check processes
Get-Process python

# Check ports
netstat -ano | findstr :8000
```

## Environment Setup

```powershell
# Create virtual environment (if needed)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start development server
.\start_simple.ps1
```

## Troubleshooting Checklist

- [ ] In correct directory (`G:\Payrol`)?
- [ ] Python installed and accessible?
- [ ] Virtual environment activated?
- [ ] Required packages installed?
- [ ] No other server running on port 8000?
- [ ] Using correct PowerShell syntax?

## Emergency Recovery

If everything fails:

1. **Stop all Python processes**:
   ```powershell
   Get-Process python | Stop-Process -Force
   ```

2. **Clean database** (if needed):
   ```powershell
   Remove-Item "payroll.db*" -Force
   ```

3. **Reinstall environment**:
   ```powershell
   Remove-Item "venv" -Recurse -Force
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Start fresh**:
   ```powershell
   .\start_simple.ps1
   ```

---

💡 **For detailed troubleshooting, see `TROUBLESHOOTING.md`** 