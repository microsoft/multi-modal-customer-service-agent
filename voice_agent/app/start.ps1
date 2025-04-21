# Write a blank line and a header  
Write-Host ""  
Write-Host "Setting up the Python virtual environment for the backend..."  
  
# Ensure the backend folder exists and change directory  
if (-not (Test-Path -Path "backend")) {  
    Write-Error "backend folder not found."  
    exit 1  
}  
Push-Location "backend"  
  
# Create virtual environment if it doesn't exist  
if (-not (Test-Path -Path ".venv")) {  
    python -m venv .venv  
}  
  
Write-Host ""  
Write-Host "Installing backend Python packages..."  
  
# Determine the python executable from the virtual environment  
$venvPython = Join-Path ".venv" "Scripts\python.exe"  
if (-not (Test-Path -Path $venvPython)) {  
    Write-Error "Could not find the virtual environment Python executable."  
    Pop-Location  
    exit 1  
}  
  
# Install backend packages  
& $venvPython -m pip install -r requirements.txt  
if ($LASTEXITCODE -ne 0) {  
    Write-Error "Backend dependency installation failed."  
    Pop-Location  
    exit 1  
}  
  
Write-Host ""  
Write-Host "Starting backend service (listening on port 8765)..."  
  
# Start the backend (using --reload for auto-restart during development)  
# Start-Process here launches the process asynchronously and returns a process object  
$backendArgs = @("app.py", "--reload")  
$backendProc = Start-Process -FilePath $venvPython -ArgumentList $backendArgs -NoNewWindow -PassThru  
  
# Return to the root folder  
Pop-Location  
  
Write-Host ""  
Write-Host "Installing frontend npm packages..."  
  
# Ensure the frontend folder exists and change directory  
if (-not (Test-Path -Path "frontend")) {  
    Write-Error "frontend folder not found."  
    exit 1  
}  
Push-Location "frontend"  
  
# Install frontend packages  
npm install  
if ($LASTEXITCODE -ne 0) {  
    Write-Error "Frontend npm installation failed."  
    Pop-Location  
    exit 1  
}  
  
Write-Host ""  
Write-Host "Starting frontend dev server..."  

# Set environment variable for frontend
$env:VITE_BACKEND_WS_URL = "ws://localhost:8765"

# Start the frontend dev server asynchronously  
$frontendProc = Start-Process -FilePath "npm" -ArgumentList @("run", "dev") -NoNewWindow -PassThru  
  
# Return to the root folder  
Pop-Location  
  
Write-Host ""  
Write-Host "Both backend and frontend services are running."  
Write-Host "Press Ctrl+C to stop."  
  
# Use a try/finally block so that when the script is interrupted (e.g., by Ctrl+C)  
# we can clean up the backend and frontend processes  
try {  
    while ($true) {  
        Start-Sleep -Seconds 1  
    }  
} finally {  
    Write-Host "Stopping services..."  
    if ($backendProc -and -not $backendProc.HasExited) {  
        Stop-Process -Id $backendProc.Id -Force  
    }  
    if ($frontendProc -and -not $frontendProc.HasExited) {  
        Stop-Process -Id $frontendProc.Id -Force  
    }  
    exit 0  
}  