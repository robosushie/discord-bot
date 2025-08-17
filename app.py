from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import threading
import os
from dotenv import load_dotenv

from src.models.database import engine
from src.models.user import Base
from src.app.routes import users
from src.discord_bot.bot import start_discord_bot

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Invitation System + Discord Bot", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Start Discord bot in background thread"""
    def run_bot():
        asyncio.run(start_discord_bot())
    
    # Start Discord bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

@app.get("/")
async def root():
    return {
        "message": "User Invitation System + Discord Bot API",
        "description": "Backend API for managing user invitations and Discord bot verification",
        "endpoints": {
            "api": "/api",
            "api_docs": "/api/docs",
            "health": "/health"
        },
        "discord_bot": "Running in background"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "User Invitation System + Discord Bot API",
        "deployment": "azure-vm",
        "message": "Backend API and Discord bot are running successfully"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting User Invitation System + Discord Bot...")
    print("🔌 API will be available at: http://localhost:8000")
    print("📚 API Documentation at: http://localhost:8000/api/docs")
    print("🤖 Discord bot will start automatically...")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    ) 