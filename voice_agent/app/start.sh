#!/usr/bin/env bash  
#  
# dev.sh  –  start backend (FastAPI) and frontend (Vite) in watch mode  
#            while taking care of Python venv / npm install, plus  
#            graceful shutdown on Ctrl-C.  
  
set -euo pipefail  
  
###############################################################################  
# Helper functions  
###############################################################################  
die () { echo "ERROR: $*" >&2; exit 1; }  
  
cleanup () {  
  echo                    # blank line  
  echo "Stopping services…"  
  [[ -n "${backend_pid:-}"  ]] && kill "$backend_pid"  2>/dev/null || true  
  [[ -n "${frontend_pid:-}" ]] && kill "$frontend_pid" 2>/dev/null || true  
  exit 0  
}  
  
trap cleanup INT TERM  
  
###############################################################################  
# Backend  
###############################################################################  
echo  
echo "Setting up the Python virtual environment for the backend..."  
  
[[ -d backend ]] || die "backend folder not found."  
pushd backend > /dev/null  
  
# ------------------------------------------------------------------  
# Create / upgrade the virtual-env  
# ------------------------------------------------------------------  
if [[ ! -d .venv ]]; then  
  # --upgrade-deps guarantees fresh pip / setuptools / wheel  
  python -m venv --upgrade-deps .venv  
else  
  # env exists – still make sure the essentials are up to date  
  .venv/bin/python -m pip install --upgrade pip setuptools wheel packaging  
fi  
  
echo  
echo "Installing backend Python packages…"  
  
venv_py=".venv/bin/python"  
[[ -x "$venv_py" ]] || { popd >/dev/null; die "Could not find the virtual-env Python executable."; }  
  
"$venv_py" -m pip install -r requirements.txt || { popd >/dev/null; die "Backend dependency installation failed."; }  
  
echo  
echo "Starting backend service (listening on port 8765)…"  
  
# Launch FastAPI (or whatever app.py holds) in the background  
"$venv_py" app.py --reload &  
backend_pid=$!  
  
popd > /dev/null  
  
###############################################################################  
# Frontend  
###############################################################################  
echo  
echo "Installing frontend npm packages…"  
  
[[ -d frontend ]] || { kill "$backend_pid"; die "frontend folder not found."; }  
pushd frontend > /dev/null  
  
npm install || { popd >/dev/null; kill "$backend_pid"; die "Frontend npm installation failed."; }  
  
echo  
echo "Starting frontend dev server…"  
  
export VITE_BACKEND_WS_URL="ws://localhost:8765"  
npm run dev &  
frontend_pid=$!  
  
popd > /dev/null  
  
###############################################################################  
# Wait forever until user presses Ctrl-C  
###############################################################################  
echo  
echo "Both backend and frontend services are running."  
echo "Press Ctrl+C to stop."  
  
# Keep script alive  
while true; do  
  sleep 1  
done