import bcrypt
import jwt
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security.utils import get_authorization_scheme_param
from starlette.requests import Request
from datetime import datetime, timedelta
from typing import Optional, Dict, Union
import aiosqlite
from database import DATABASE_PATH

# JWT Configuration
SECRET_KEY = "your_super_secret_key_for_jwt_token_generation"  # In production, store securely
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Custom OAuth2 scheme that checks both cookies and headers
class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        # Check cookies first
        token = request.cookies.get("access_token")
        
        # If not in cookies, check header
        if not token:
            authorization = request.headers.get("Authorization")
            scheme, param = get_authorization_scheme_param(authorization)
            if scheme.lower() == "bearer":
                token = param
        
        # Handle authentication requirement
        if not token and self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return token

# Create OAuth2 schemes
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="users/token", auto_error=True)
oauth2_scheme_optional = OAuth2PasswordBearerWithCookie(tokenUrl="users/token", auto_error=False)

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    """Generate a bcrypt hash for the password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

async def authenticate_user(username: str, password: str):
    """Authenticate a user by username and password."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = await cursor.fetchone()
    
    if not user:
        return False
    if not verify_password(password, user['password']):
        return False
    return dict(user)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_token_from_request(request: Request) -> Optional[str]:
    """Get token from cookies or authorization header."""
    # Check cookies first
    token = request.cookies.get("access_token")
    
    # If not in cookies, check authorization header
    if not token:
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() != "bearer":
                token = None
    
    return token

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = await cursor.fetchone()
    
    if user is None:
        raise credentials_exception
    return dict(user)

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional)):
    """
    Similar to get_current_user, but returns None if no valid token is provided,
    instead of raising an exception.
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except jwt.PyJWTError:
        return None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = await cursor.fetchone()
    
    if user is None:
        return None
    
    return dict(user)

async def verify_token(token: str) -> bool:
    """Verify if a token is valid without returning user details."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return False
        
        # Check if user exists
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            user_exists = await cursor.fetchone() is not None
        
        return user_exists
    except jwt.PyJWTError:
        return False