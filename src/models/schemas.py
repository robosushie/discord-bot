from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    name: str
    college: str
    branch: str
    year: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    token: str
    is_verified: bool
    token_created_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserVerification(BaseModel):
    email: str
    token: str

class DiscordVerification(BaseModel):
    email: str
    token: str
    discord_user_id: str

class VerificationResponse(BaseModel):
    success: bool
    message: str

class DiscordVerificationResponse(BaseModel):
    success: bool
    message: str
    discord_user_id: Optional[str] = None

class CSVUploadResponse(BaseModel):
    total_processed: int
    newly_added: int
    skipped: int
    newly_added_users: List[UserResponse]

class EmailSendResponse(BaseModel):
    success: bool
    message: str
    emails_sent: int 