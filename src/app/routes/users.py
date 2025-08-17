from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
import io
from typing import List
from datetime import datetime, timezone

from src.models.database import get_db
from src.models.user import User
from src.models.schemas import (
    UserCreate, UserResponse, UserVerification, VerificationResponse,
    CSVUploadResponse, EmailSendResponse
)
from src.utils.helpers import generate_token, is_token_expired, send_verification_email
from src.app.dependencies import api_key_dependency

router = APIRouter(tags=["users"])

@router.post("/upload-csv", response_model=CSVUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Upload CSV file with user data and add to database"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Validate required columns
        required_columns = ['email', 'name', 'college', 'branch', 'year']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        newly_added = 0
        skipped = 0
        newly_added_users = []
        
        for _, row in df.iterrows():
            email = row['email'].strip().lower()
            name = row['name'].strip()
            college = row['college'].strip()
            branch = row['branch'].strip()
            year = int(row['year'])
            
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                skipped += 1
                continue
            
            # Generate token
            token = generate_token()
            
            # Create new user
            new_user = User(
                email=email,
                name=name,
                college=college,
                branch=branch,
                year=year,
                token=token,
                is_verified=False
            )
            
            db.add(new_user)
            newly_added += 1
        
        db.commit()
        
        # Get newly added users for response
        if newly_added > 0:
            newly_added_users = db.query(User).filter(
                User.email.in_([row['email'].strip().lower() for _, row in df.iterrows()])
            ).all()
        
        return CSVUploadResponse(
            total_processed=len(df),
            newly_added=newly_added,
            skipped=skipped,
            newly_added_users=newly_added_users
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.post("/send-emails", response_model=EmailSendResponse)
async def send_verification_emails(
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Send verification emails to all unverified users"""
    try:
        # Get all unverified users
        unverified_users = db.query(User).filter(User.is_verified == False).all()
        
        if not unverified_users:
            return EmailSendResponse(
                success=True,
                message="No unverified users found",
                emails_sent=0
            )
        
        emails_sent = 0
        failed_emails = []
        
        for user in unverified_users:
            if send_verification_email(user.email, user.name, user.token):
                emails_sent += 1
            else:
                failed_emails.append(user.email)
        
        message = f"Successfully sent {emails_sent} verification emails"
        if failed_emails:
            message += f". Failed to send {len(failed_emails)} emails"
        
        return EmailSendResponse(
            success=True,
            message=message,
            emails_sent=emails_sent
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending emails: {str(e)}")

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Get all users"""
    users = db.query(User).all()
    return users

@router.post("/refresh-token/{user_id}")
async def refresh_token(
    user_id: int, 
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Refresh token for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new token
    new_token = generate_token()
    user.token = new_token
    user.token_created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {
        "message": "Token refreshed successfully",
        "new_token": new_token
    }

@router.post("/verify", response_model=VerificationResponse)
async def verify_user(
    verification: UserVerification,
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Verify user with email and token"""
    user = db.query(User).filter(User.email == verification.email).first()
    
    if not user:
        return VerificationResponse(
            success=False,
            message="User not found with this email"
        )
    
    if user.token != verification.token:
        return VerificationResponse(
            success=False,
            message="Invalid verification token"
        )
    
    if user.is_verified:
        return VerificationResponse(
            success=False,
            message="User is already verified"
        )
    
    # Check if token is expired
    if is_token_expired(user.token_created_at):
        return VerificationResponse(
            success=False,
            message="Verification token has expired"
        )
    
    # Mark user as verified
    user.is_verified = True
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return VerificationResponse(
        success=True,
        message="User verified successfully"
    )

@router.post("/verify-discord")
async def verify_user_discord(
    verification: dict,
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Verify user with email and token for Discord bot"""
    email = verification.get('email')
    token = verification.get('token')
    discord_user_id = verification.get('discord_user_id')
    
    if not all([email, token, discord_user_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return {
            "success": False,
            "message": "User not found with this email"
        }
    
    if user.token != token:
        return {
            "success": False,
            "message": "Invalid verification token"
        }
    
    if user.is_verified:
        return {
            "success": False,
            "message": "User is already verified"
        }
    
    # Check if token is expired
    if is_token_expired(user.token_created_at):
        return {
            "success": False,
            "message": "Verification token has expired"
        }
    
    # Mark user as verified
    user.is_verified = True
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "success": True,
        "message": "User verified successfully",
        "discord_user_id": discord_user_id
    }

@router.delete("/all")
async def delete_all_users(
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Delete all users from the database"""
    try:
        db.query(User).delete()
        db.commit()
        return {"message": "All users deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting users: {str(e)}")

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    api_key: str = api_key_dependency
):
    """Delete a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"} 