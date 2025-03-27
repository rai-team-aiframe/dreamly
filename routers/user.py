from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List, Optional
import aiosqlite

from database import DATABASE_PATH
from models import UserCreate, User, UserProfile, Token, UserUpdate
from auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    get_current_user_optional,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

templates = Jinja2Templates(directory="templates")

@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate, response: Response):
    """Register a new user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if username already exists
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (user_data.username,))
        if await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (user_data.email,))
        if await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Insert new user
        cursor = await db.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (user_data.username, user_data.email, hashed_password)
        )
        await db.commit()
        
        # Get the created user
        user_id = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    # Set cookie with the token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/"
    )
    
    return dict(user)

@router.post("/token", response_model=Token)
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get an access token."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    # Set cookie with the token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    """Logout by clearing the token cookie."""
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get the current authenticated user."""
    return current_user

@router.put("/me", response_model=User)
async def update_user(user_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """Update the current user's profile."""
    update_fields = {}
    update_values = []
    
    # Check which fields to update
    if user_data.email is not None:
        update_fields["email"] = user_data.email
        update_values.append(user_data.email)
    
    if user_data.bio is not None:
        update_fields["bio"] = user_data.bio
        update_values.append(user_data.bio)
    
    if user_data.password is not None:
        update_fields["password"] = get_password_hash(user_data.password)
        update_values.append(update_fields["password"])
    
    if not update_fields:
        return current_user  # Nothing to update
    
    # Build the SQL query
    set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
    update_values.append(current_user["id"])
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        await db.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?",
            update_values
        )
        await db.commit()
        
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],))
        updated_user = await cursor.fetchone()
    
    return dict(updated_user)

@router.get("/profile/{username}", response_model=UserProfile)
async def get_user_profile(username: str, request: Request):
    """Get a user's profile."""
    # Get current user if authenticated
    from auth import get_token_from_request, get_current_user_optional
    token = await get_token_from_request(request)
    current_user = await get_current_user_optional(token) if token else None
    current_user_id = current_user["id"] if current_user else None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get the user
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = await cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get follower count
        cursor = await db.execute("SELECT COUNT(*) FROM followers WHERE followed_id = ?", (user['id'],))
        follower_count = (await cursor.fetchone())[0]
        
        # Get following count
        cursor = await db.execute("SELECT COUNT(*) FROM followers WHERE follower_id = ?", (user['id'],))
        following_count = (await cursor.fetchone())[0]
        
        # Get post count
        cursor = await db.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user['id'],))
        post_count = (await cursor.fetchone())[0]
        
        # Check if the current user is following this user (if authenticated)
        is_following = False
        if current_user_id:
            cursor = await db.execute(
                "SELECT * FROM followers WHERE follower_id = ? AND followed_id = ?",
                (current_user_id, user['id'])
            )
            is_following = await cursor.fetchone() is not None
    
    return {
        **dict(user),
        "follower_count": follower_count,
        "following_count": following_count,
        "post_count": post_count,
        "is_following": is_following
    }

@router.post("/follow/{user_id}")
async def follow_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Follow or unfollow a user."""
    if current_user['id'] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if the user exists
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        if not await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already following
        cursor = await db.execute(
            "SELECT * FROM followers WHERE follower_id = ? AND followed_id = ?",
            (current_user['id'], user_id)
        )
        
        if await cursor.fetchone():
            # Already following, unfollow
            await db.execute(
                "DELETE FROM followers WHERE follower_id = ? AND followed_id = ?",
                (current_user['id'], user_id)
            )
            message = "Unfollowed successfully"
            action = "unfollowed"
        else:
            # Not following, follow
            await db.execute(
                "INSERT INTO followers (follower_id, followed_id) VALUES (?, ?)",
                (current_user['id'], user_id)
            )
            message = "Followed successfully"
            action = "followed"
        
        await db.commit()
    
    return {"message": message, "action": action}

@router.get("/feed", response_model=List[dict])
async def get_user_feed(current_user: dict = Depends(get_current_user)):
    """Get posts from users the current user follows."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT p.*, u.username, 
                  (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                  (SELECT EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?)) as liked_by_user
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id IN (
                SELECT followed_id FROM followers WHERE follower_id = ?
            ) OR p.user_id = ?
            ORDER BY p.created_at DESC
        """, (current_user['id'], current_user['id'], current_user['id']))
        
        posts = [dict(row) for row in await cursor.fetchall()]
    
    return posts

@router.get("/followers/{user_id}", response_model=List[dict])
async def get_followers(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get a list of users who follow the specified user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT u.id, u.username, u.email, u.bio, u.created_at,
                  (SELECT EXISTS(SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = u.id)) as is_followed
            FROM users u
            JOIN followers f ON u.id = f.follower_id
            WHERE f.followed_id = ?
            ORDER BY u.username
        """, (current_user['id'], user_id))
        
        followers = [dict(row) for row in await cursor.fetchall()]
    
    return followers

@router.get("/following/{user_id}", response_model=List[dict])
async def get_following(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get a list of users the specified user follows."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT u.id, u.username, u.email, u.bio, u.created_at,
                  (SELECT EXISTS(SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = u.id)) as is_followed
            FROM users u
            JOIN followers f ON u.id = f.followed_id
            WHERE f.follower_id = ?
            ORDER BY u.username
        """, (current_user['id'], user_id))
        
        following = [dict(row) for row in await cursor.fetchall()]
    
    return following

@router.get("/search/{query}", response_model=List[dict])
async def search_users(query: str, current_user: dict = Depends(get_current_user)):
    """Search for users by username or email."""
    search_pattern = f"%{query}%"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT u.id, u.username, u.email, u.bio, u.created_at,
                  (SELECT EXISTS(SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = u.id)) as is_followed
            FROM users u
            WHERE u.username LIKE ? OR u.email LIKE ?
            ORDER BY u.username
            LIMIT 20
        """, (current_user['id'], search_pattern, search_pattern))
        
        users = [dict(row) for row in await cursor.fetchall()]
    
    return users

@router.get("/liked", response_model=List[dict])
async def get_liked_posts(current_user: dict = Depends(get_current_user)):
    """Get posts liked by the current user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute("""
            SELECT p.*, u.username, 
                  (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                  1 as liked_by_user
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN likes l ON p.id = l.post_id
            WHERE l.user_id = ?
            ORDER BY l.created_at DESC
        """, (current_user['id'],))
        
        liked_posts = [dict(row) for row in await cursor.fetchall()]
    
    return liked_posts