from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import streamlit.web.bootstrap as bootstrap
import streamlit as st
import subprocess
import sys
import os
from pathlib import Path
import threading
import time
import webbrowser

# Import the FastAPI app
from src.app.app import app as fastapi_app

# Create the main app
app = FastAPI(title="User Invitation System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the FastAPI app at /api
app.mount("/api", fastapi_app)

# Streamlit app directory
STREAMLIT_APP_DIR = Path(__file__).parent / "src" / "app" / "dashboard"
STREAMLIT_PORT = 8501

# Global variable to track if Streamlit is running
streamlit_process = None

def start_streamlit():
    """Start Streamlit in a separate thread"""
    global streamlit_process
    
    try:
        # Change to Streamlit app directory
        os.chdir(STREAMLIT_APP_DIR)
        
        # Start Streamlit process
        streamlit_process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "main.py",
            "--server.port", str(STREAMLIT_PORT),
            "--server.address", "localhost",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.runOnSave", "false"
        ])
        
        print(f"✅ Streamlit started on port {STREAMLIT_PORT}")
        
    except Exception as e:
        print(f"❌ Error starting Streamlit: {e}")

def start_streamlit_background():
    """Start Streamlit in background thread"""
    thread = threading.Thread(target=start_streamlit, daemon=True)
    thread.start()
    
    # Wait a bit for Streamlit to start
    time.sleep(3)
    
    # Open dashboard in browser
    try:
        webbrowser.open(f"http://localhost:{STREAMLIT_PORT}")
    except:
        pass

@app.on_event("startup")
async def startup_event():
    """Start Streamlit when FastAPI starts"""
    start_streamlit_background()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop Streamlit when FastAPI stops"""
    global streamlit_process
    if streamlit_process:
        streamlit_process.terminate()
        print("✅ Streamlit stopped")

@app.get("/")
async def root():
    return {
        "message": "User Invitation System",
        "endpoints": {
            "api": "/api",
            "dashboard": f"/dashboard (http://localhost:{STREAMLIT_PORT})",
            "api_docs": "/api/docs"
        }
    }

@app.get("/dashboard")
async def dashboard_root():
    """Redirect to Streamlit dashboard"""
    return RedirectResponse(url=f"http://localhost:{STREAMLIT_PORT}")

@app.get("/dashboard/{path:path}")
async def dashboard_path(path: str):
    """Redirect to Streamlit dashboard with path"""
    return RedirectResponse(url=f"http://localhost:{STREAMLIT_PORT}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global streamlit_process
    
    streamlit_status = "running" if streamlit_process and streamlit_process.poll() is None else "stopped"
    
    return {
        "status": "healthy",
        "fastapi": "running",
        "streamlit": streamlit_status,
        "streamlit_port": STREAMLIT_PORT
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting User Invitation System...")
    print(f"📊 Dashboard will be available at: http://localhost:{STREAMLIT_PORT}")
    print("🔌 API will be available at: http://localhost:8000")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    ) 