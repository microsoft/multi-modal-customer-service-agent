#!/bin/sh
# This script sets up and starts the backend and frontend for local development.
set -eu

# --------------------------- Start the Backend Service ---------------------------  
echo ""
echo "Setting up the Python virtual environment for the backend..."

cd backend || { echo "backend folder not found."; exit 1; }

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

VENV_PYTHON="./.venv/bin/python"

# Ensure pip is available in the virtualenv
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "pip not found in venv. Attempting to install pip..."
    if ! "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
        echo "ensurepip failed. Attempting curl get-pip.py..."
        curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        "$VENV_PYTHON" get-pip.py
        rm -f get-pip.py
    fi
    # Double-check pip is now available
    if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
        echo "Failed to install pip in the virtual environment."
        exit 1
    fi
fi

echo "" 
echo "Installing backend Python packages..."
if ! "$VENV_PYTHON" -m pip install -r requirements.txt; then
    echo "Backend dependency installation failed."
    exit 1
fi

echo ""
echo "Starting backend service (listening on port 8765)..."
"$VENV_PYTHON" app.py --reload &
BACKEND_PID=$!

cd ..

# --------------------------- Start the Frontend Service ---------------------------
echo ""
echo "Installing frontend npm packages..."

cd frontend || { echo "frontend folder not found."; exit 1; }
if ! npm install; then
    echo "Frontend npm installation failed."
    exit 1
fi
VITE_BACKEND_WS_URL="ws://localhost:8765"

echo ""
echo "Starting frontend dev server..."
npm run dev &
FRONTEND_PID=$!

cd ..

# --------------------------- Clean-up on Exit --------------------------- 
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

echo ""
echo "Both backend and frontend services are running."
echo "Press Ctrl+C to stop."

wait
