import random
import string
import os
from typing import Optional
from datetime import datetime, timedelta, timezone
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

def generate_token(length: int = 6) -> str:
    """Generate a random alphanumeric token of specified length"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def is_token_expired(token_created_at: datetime, expiry_days: Optional[int] = None) -> bool:
    """Check if a token has expired based on creation date"""
    if expiry_days is None:
        expiry_days = int(os.getenv("TOKEN_EXPIRY_DAYS", 7))
    
    expiry_date = token_created_at + timedelta(days=expiry_days)
    return datetime.now(timezone.utc) > expiry_date

def send_verification_email(email: str, name: str, token: str) -> bool:
    """Send verification email using SendGrid"""
    try:
        sg = SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
        
        # Email template
        subject = "Verify Your Account"
        html_content = f"""
        <html>
        <body>
            <h2>Welcome {name}!</h2>
            <p>Thank you for registering. Please use the following verification code to complete your registration:</p>
            <h1 style="color: #007bff; font-size: 2em; text-align: center; padding: 20px; background: #f8f9fa; border-radius: 5px;">{token}</h1>
            <p>This code will expire in {os.getenv('TOKEN_EXPIRY_DAYS', 7)} days.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <br>
            <p>Best regards,<br>Your Team</p>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=os.getenv("SENDGRID_FROM_EMAIL"),
            to_emails=email,
            subject=subject,
            html_content=html_content
        )
        
        response = sg.send(message)
        return response.status_code == 202
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def mask_token(token: str) -> str:
    """Mask a token for display purposes (show only first and last character)"""
    if len(token) <= 2:
        return token
    return token[0] + "*" * (len(token) - 2) + token[-1] 