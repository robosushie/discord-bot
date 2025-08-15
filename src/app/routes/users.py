from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd
import io
from typing import List

from src.models.database import get_db
from src.models.user import User
from src.models.schemas import (
    UserCreate, UserResponse, UserVerification, VerificationResponse,
    CSVUploadResponse, EmailSendResponse
)
from src.utils.helpers import generate_token, is_token_expired, send_verification_email

router = APIRouter(tags=["users"])

@router.post("/upload-csv", response_model=CSVUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
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
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain columns: {required_columns}"
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
            
            # Generate unique token
            while True:
                token = generate_token()
                if not db.query(User).filter(User.token == token).first():
                    break
            
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
                User.id.in_([u.id for u in db.query(User).order_by(User.id.desc()).limit(newly_added).all()])
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
async def send_emails(
    user_ids: List[int],
    db: Session = Depends(get_db)
):
    """Send verification emails to specified users"""
    if not user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="No users found")
    
    emails_sent = 0
    failed_emails = []
    
    for user in users:
        if send_verification_email(user.email, user.name, user.token):
            emails_sent += 1
        else:
            failed_emails.append(user.email)
    
    message = f"Successfully sent {emails_sent} emails"
    if failed_emails:
        message += f". Failed to send to: {', '.join(failed_emails)}"
    
    return EmailSendResponse(
        success=emails_sent > 0,
        message=message,
        emails_sent=emails_sent
    )

@router.get("/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).all()
    return users

@router.post("/refresh-token/{user_id}")
async def refresh_token(user_id: int, db: Session = Depends(get_db)):
    """Refresh token for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate new unique token
    while True:
        new_token = generate_token()
        if not db.query(User).filter(User.token == new_token).first():
            break
    
    # Update user with new token and reset verification status
    user.token = new_token
    user.is_verified = False
    # Update token creation timestamp
    from datetime import datetime, timezone
    user.token_created_at = datetime.now(timezone.utc)
    
    try:
        db.commit()
        return {"message": "Token refreshed successfully", "new_token": new_token}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")

@router.post("/verify", response_model=VerificationResponse)
async def verify_user(
    verification: UserVerification,
    db: Session = Depends(get_db)
):
    """Verify user with email and token"""
    user = db.query(User).filter(User.email == verification.email).first()
    
    if not user:
        return VerificationResponse(
            success=False,
            message="User not found"
        )
    
    if user.token != verification.token:
        return VerificationResponse(
            success=False,
            message="Invalid token"
        )
    
    if user.is_verified:
        return VerificationResponse(
            success=False,
            message="User already verified"
        )
    
    if is_token_expired(user.token_created_at):
        return VerificationResponse(
            success=False,
            message="Token has expired"
        )
    
    # Mark user as verified
    user.is_verified = True
    db.commit()
    
    return VerificationResponse(
        success=True,
        message="User verified successfully"
    )

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")

@router.delete("/all")
async def delete_all_users(db: Session = Depends(get_db)):
    """Delete all users from the database"""
    try:
        # Get total user count
        total_users = db.query(User).count()
        
        if total_users == 0:
            return {"message": "No users to delete", "deleted_count": 0}
        
        # Delete all users
        deleted_count = db.query(User).delete()
        db.commit()
        
        return {
            "message": f"Successfully deleted all {deleted_count} users",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all users: {str(e)}") 