from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get SECRET_KEY from environment
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Verify the x-api-key header against SECRET_KEY
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401, 
            detail="x-api-key header is required"
        )
    
    if x_api_key != SECRET_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key"
        )
    
    return x_api_key

# Create a dependency that can be used in route decorators
api_key_dependency = Depends(verify_api_key) 