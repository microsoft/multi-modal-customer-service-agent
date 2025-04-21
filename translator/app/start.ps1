# Ensure we exit on any error
$ErrorActionPreference = "Stop"

Write-Host "`nCreating python virtual environment '.venv'`n" -ForegroundColor Cyan

# Check Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found. Please install Python 3 and ensure it's in your PATH." -ForegroundColor Red
    exit 1
}

try {
    Set-Location ./backend -ErrorAction Stop
}
catch {
    Write-Host "ERROR: Failed to enter backend directory. Does it exist?" -ForegroundColor Red
    exit 1
}

# Create virtual environment with visible output
try {
    Write-Host "Using Python at $($pythonCmd.Source)" -ForegroundColor DarkGray
    & $pythonCmd.Source -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed"
    }
}
catch {
    Write-Host "ERROR: Failed to create virtual environment. Check Python installation and venv module availability." -ForegroundColor Red
    exit 1
}

# Verify virtual environment creation
$venvPythonPath = if (Test-Path -Path "/usr") {
    "$(Get-Location)/.venv/bin/python"  # Linux/Mac
} else {
    "$(Get-Location)/.venv/Scripts/python.exe"  # Windows
}

if (-not (Test-Path $venvPythonPath)) {
    Write-Host "ERROR: Virtual environment Python not found at $venvPythonPath" -ForegroundColor Red
    exit 1
}

Write-Host "`nRestoring backend python packages`n" -ForegroundColor Cyan

# Install requirements with visible output
try {
    & $venvPythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed with exit code $LASTEXITCODE"
    }
}
catch {
    Write-Host "ERROR: Failed to restore backend packages. Check:" -ForegroundColor Red
    Write-Host "1. requirements.txt file exists and is valid"
    Write-Host "2. Internet connection is available"
    Write-Host "3. Packages in requirements.txt are compatible"
    Write-Host "4. Python version matches package requirements"
    Write-Host "5. Check above pip output for specific errors`n"
    exit $LASTEXITCODE
}

Write-Host "`nRestoring frontend npm packages`n" -ForegroundColor Cyan

try {
    Set-Location ../frontend -ErrorAction Stop
}
catch {
    Write-Host "ERROR: Failed to enter frontend directory. Does it exist?" -ForegroundColor Red
    exit 1
}

try {
    npm install
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed"
    }
}
catch {
    Write-Host "ERROR: Failed to restore frontend packages. Check:" -ForegroundColor Red
    Write-Host "1. network connectivity"
    Write-Host "2. package.json validity"
    Write-Host "3. npm registry access"
    Write-Host "4. Check above npm output for specific errors`n"
    exit $LASTEXITCODE
}

Write-Host "`nBuilding frontend`n" -ForegroundColor Cyan

try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "npm build failed"
    }
}
catch {
    Write-Host "ERROR: Failed to build frontend. Check:" -ForegroundColor Red
    Write-Host "1. Build script in package.json"
    Write-Host "2. Build dependencies are installed"
    Write-Host "3. Node.js version compatibility"
    Write-Host "4. Check above build output for specific errors`n"
    exit $LASTEXITCODE
}

Write-Host "`nStarting backend server`n" -ForegroundColor Cyan

try {
    Set-Location ../backend -ErrorAction Stop
}
catch {
    Write-Host "ERROR: Failed to return to backend directory" -ForegroundColor Red
    exit 1
}

try {
    Start-Process "http://127.0.0.1:8765"  # Open browser first
    & $venvPythonPath -m app --reload
    if ($LASTEXITCODE -ne 0) {
        throw "Backend server failed to start"
    }
}
catch {
    Write-Host "ERROR: Failed to start backend. Check:" -ForegroundColor Red
    Write-Host "1. App module (app) exists and is properly configured"
    Write-Host "2. Port 8765 is available"
    Write-Host "3. Database connections (if any)"
    Write-Host "4. Check above Python output for specific errors`n"
    exit $LASTEXITCODE
}