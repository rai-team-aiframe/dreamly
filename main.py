import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException, status, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite
import base64
from typing import Optional
import jwt
from datetime import datetime, timedelta

from database import initialize_database, DATABASE_PATH
from routers import user, post
from auth import (
    get_current_user, 
    get_current_user_optional, 
    get_token_from_request, 
    oauth2_scheme,
    oauth2_scheme_optional,
    SECRET_KEY,
    ALGORITHM
)

# Initialize the database
initialize_database()

# Create FastAPI app
app = FastAPI(title="ImageShare", description="A social media app for sharing AI-generated images")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(user.router)
app.include_router(post.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page or landing page based on authentication status."""
    # Extract token
    token = await get_token_from_request(request)
    
    # Get user if token exists
    user = await get_current_user_optional(token) if token else None
    
    if user:
        # User is authenticated, render the home page
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        # User is not authenticated, render the landing page
        return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login page."""
    # Check if user is already logged in
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if user:
        # Already logged in, redirect to home
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render the registration page."""
    # Check if user is already logged in
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if user:
        # Already logged in, redirect to home
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/explore", response_class=HTMLResponse)
async def explore_page(request: Request):
    """Render the explore page."""
    return templates.TemplateResponse("explore.html", {"request": request})

@app.get("/create", response_class=HTMLResponse)
async def create_post_page(request: Request):
    """Render the create post page."""
    # Extract token and check authentication
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if not user:
        # Not authenticated, redirect to login
        return RedirectResponse(url="/login?next=/create", status_code=302)
    
    return templates.TemplateResponse("create_post.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Render the user's profile page."""
    # Extract token and check authentication
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if not user:
        # Not authenticated, redirect to login
        return RedirectResponse(url="/login?next=/profile", status_code=302)
    
    # Render profile with the user's username
    return templates.TemplateResponse("profile.html", {"request": request, "username": user["username"]})

@app.get("/profile/{username}", response_class=HTMLResponse)
async def user_profile_page(request: Request, username: str):
    """Render another user's profile page."""
    # Extract token and check authentication
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if not user:
        # Not authenticated, redirect to login
        return RedirectResponse(url=f"/login?next=/profile/{username}", status_code=302)
    
    return templates.TemplateResponse("profile.html", {"request": request, "username": username})

@app.get("/post/{post_id}", response_class=HTMLResponse)
async def view_post_page(request: Request, post_id: int):
    """Render the page to view a specific post."""
    # Extract token to check if user is authenticated (but don't require it)
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    return templates.TemplateResponse("view_post.html", {"request": request, "post_id": post_id})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render the user settings page."""
    # Extract token and check authentication
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if not user:
        # Not authenticated, redirect to login
        return RedirectResponse(url="/login?next=/settings", status_code=302)
    
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/followers/{username}", response_class=HTMLResponse)
async def followers_page(request: Request, username: str):
    """Render the followers page for a user."""
    # Extract token and check authentication
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if not user:
        # Not authenticated, redirect to login
        return RedirectResponse(url=f"/login?next=/followers/{username}", status_code=302)
    
    return templates.TemplateResponse("followers.html", {"request": request, "username": username})

@app.get("/following/{username}", response_class=HTMLResponse)
async def following_page(request: Request, username: str):
    """Render the following page for a user."""
    # Extract token and check authentication
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if not user:
        # Not authenticated, redirect to login
        return RedirectResponse(url=f"/login?next=/following/{username}", status_code=302)
    
    return templates.TemplateResponse("following.html", {"request": request, "username": username})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Render the search page."""
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """API endpoint for health checking."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/api/auth/status")
async def auth_status(request: Request):
    """Check user's authentication status."""
    # Extract token
    token = await get_token_from_request(request)
    user = await get_current_user_optional(token) if token else None
    
    if user:
        return {
            "authenticated": True, 
            "username": user["username"],
            "user_id": user["id"]
        }
    else:
        return {"authenticated": False}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware to handle authentication and redirects."""
    # Public paths that don't require authentication
    public_paths = [
        "/login", 
        "/register", 
        "/static", 
        "/users/token", 
        "/users/register", 
        "/api/health",
        "/api/auth/status",
        "/explore",
        "/",
    ]
    
    # Check if current path is in public paths or starts with one
    is_public = False
    for path in public_paths:
        if request.url.path == path or request.url.path.startswith(path + "/"):
            is_public = True
            break
        
    # API paths that return JSON responses for 401
    api_paths = ["/users/", "/posts/"]
    is_api = False
    for path in api_paths:
        if request.url.path.startswith(path):
            is_api = True
            break
    
    # Continue processing for public paths
    if is_public:
        return await call_next(request)
    
    # Check for token
    token = await get_token_from_request(request)
    if not token:
        if is_api:
            # API paths return JSON error
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"}
            )
        else:
            # UI paths redirect to login
            return RedirectResponse(
                url=f"/login?next={request.url.path}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Verify token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise jwt.PyJWTError("Invalid token")
    except jwt.PyJWTError:
        if is_api:
            # API paths return JSON error
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"}
            )
        else:
            # UI paths redirect to login
            return RedirectResponse(
                url=f"/login?next={request.url.path}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Token is valid, continue processing
    response = await call_next(request)
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)