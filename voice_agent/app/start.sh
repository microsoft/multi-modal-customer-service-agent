#!/bin/sh  
# This script sets up and starts both the backend and the frontend for local development.  
# The backend is run with a Python virtual environment and the frontend uses Vite’s dev server.  
  
# --------------------------- Start the Backend Service ---------------------------  
echo ""  
echo "Setting up the Python virtual environment for the backend..."  
  
cd backend || { echo "backend folder not found."; exit 1; }  
  
# Create virtual environment if it doesn't exist  
if [ ! -d ".venv" ]; then  
    python3 -m venv .venv  
fi  
  
echo ""  
echo "Installing backend Python packages..."  
./.venv/bin/python -m pip install -r requirements.txt || { echo "Backend dependency installation failed."; exit 1; }  
  
echo ""  
echo "Starting backend service (listening on port 8765)..."  
# Use --reload for auto-restarting during development  
./.venv/bin/python app.py --reload &  
BACKEND_PID=$!  
  
cd ..  
  
# --------------------------- Start the Frontend Service ---------------------------  
echo ""  
echo "Installing frontend npm packages..."  
  
cd frontend || { echo "frontend folder not found."; exit 1; }  
npm install || { echo "Frontend npm installation failed."; exit 1; }  
  
# Note:  
# • The .env file for the frontend should be placed in the frontend directory (i.e., ./frontend/.env)  
# • This file can contain environment variables such as BACKEND_WS_URL that Vite will load.  
#  
# Example .env file:  
export VITE_BACKEND_WS_URL="ws://localhost:8765"  
  
echo ""  
echo "Starting frontend dev server..."  
npm run dev &  
FRONTEND_PID=$!  
  
cd ..  
  
# --------------------------- Clean-up on Exit ---------------------------  
trap "echo 'Stopping services...'; kill $BACKEND_PID; kill $FRONTEND_PID; exit 0" INT TERM  
  
echo ""  
echo "Both backend and frontend services are running."  
echo "Press Ctrl+C to stop."  
  
wait  