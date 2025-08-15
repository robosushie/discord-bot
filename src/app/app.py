from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.models.database import engine
from src.models.user import Base
from .routes import users

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Invitation System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "User Invitation System API"} 