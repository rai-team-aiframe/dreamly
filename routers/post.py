from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response
from fastapi.responses import JSONResponse
from typing import List, Optional
import base64
import aiosqlite
import json

from together import Together
from database import DATABASE_PATH
from models import PostCreate, Post
from auth import get_current_user, get_current_user_optional, get_token_from_request

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)

# Initialize the Together API client
together_client = Together(api_key="d292b79dda4f87085a633743a84dcc46ab4d70fdee4b25b7acb4691b80c7ad92")

@router.post("/", response_model=Post)
async def create_post(post_data: PostCreate, current_user: dict = Depends(get_current_user)):
    """Create a new post with an AI-generated image."""
    # Generate image using Together API
    try:
        prompt = post_data.prompt.strip()
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt cannot be empty"
            )
            
        response = await together_client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=1024,  # Reduced size for faster generation
            height=1024,
            steps=4,
            n=1,
            response_format="b64_json",
            stop=[]
        )
        
        if not hasattr(response, 'data') or not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No image data received from API"
            )
            
        image_data = response.data[0].b64_json
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating image: {str(e)}"
        )
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Insert new post
            cursor = await db.execute(
                "INSERT INTO posts (user_id, prompt, image_data, caption) VALUES (?, ?, ?, ?)",
                (current_user['id'], post_data.prompt, image_data, post_data.caption)
            )
            await db.commit()
            
            # Get the created post
            post_id = cursor.lastrowid
            cursor = await db.execute("""
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      (SELECT EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?)) as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ?
            """, (current_user['id'], post_id))
            post = await cursor.fetchone()
            
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error retrieving created post"
                )
        
        return dict(post)
    except Exception as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving post: {str(e)}"
        )

@router.get("/{post_id}", response_model=Post)
async def get_post(post_id: int, request: Request):
    """Get a specific post."""
    # Get current user if authenticated
    token = await get_token_from_request(request)
    current_user = await get_current_user_optional(token) if token else None
    current_user_id = current_user["id"] if current_user else None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Build query with or without liked_by_user
        if current_user_id:
            query = """
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      (SELECT EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?)) as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ?
            """
            cursor = await db.execute(query, (current_user_id, post_id))
        else:
            query = """
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      0 as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ?
            """
            cursor = await db.execute(query, (post_id,))
        
        post = await cursor.fetchone()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return dict(post)

@router.post("/like/{post_id}")
async def like_post(post_id: int, current_user: dict = Depends(get_current_user)):
    """Like or unlike a post."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if the post exists
        cursor = await db.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        if not await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check if already liked
        cursor = await db.execute(
            "SELECT * FROM likes WHERE user_id = ? AND post_id = ?",
            (current_user['id'], post_id)
        )
        
        if await cursor.fetchone():
            # Already liked, unlike
            await db.execute(
                "DELETE FROM likes WHERE user_id = ? AND post_id = ?",
                (current_user['id'], post_id)
            )
            message = "Post unliked successfully"
            action = "unliked"
        else:
            # Not liked, like
            await db.execute(
                "INSERT INTO likes (user_id, post_id) VALUES (?, ?)",
                (current_user['id'], post_id)
            )
            message = "Post liked successfully"
            action = "liked"
        
        # Get updated like count
        cursor = await db.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,))
        like_count = (await cursor.fetchone())[0]
        
        await db.commit()
    
    return {"message": message, "action": action, "like_count": like_count}

@router.get("/", response_model=List[dict])
async def get_explore_posts(request: Request, filter: str = "latest", page: int = 1, category: str = None):
    """Get posts for the explore section."""
    # Extract token from request to check if user is authenticated
    token = await get_token_from_request(request)
    current_user = await get_current_user_optional(token) if token else None
    current_user_id = current_user["id"] if current_user else None
    
    limit = 12
    offset = (page - 1) * limit
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Base query
        query = """
            SELECT p.*, u.username, 
                  (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count
        """
        
        # Add liked_by_user field if user is authenticated
        if current_user_id:
            query += f", (SELECT EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?)) as liked_by_user"
        else:
            query += ", 0 as liked_by_user"
            
        query += """
            FROM posts p
            JOIN users u ON p.user_id = u.id
        """
        
        # Add category filter if provided
        params = []
        if current_user_id:
            params.append(current_user_id)
            
        if category:
            query += " WHERE (p.caption LIKE ? OR p.prompt LIKE ?)"
            params.extend([f"%{category}%", f"%{category}%"])
        
        # Add ordering based on filter type
        if filter == "latest":
            query += " ORDER BY p.created_at DESC"
        elif filter == "popular":
            query += " ORDER BY like_count DESC"
        elif filter == "trending":
            # Simplified trending algorithm - recent posts with high engagement
            query += " ORDER BY (like_count * 10 + (julianday('now') - julianday(p.created_at)) * 86400) DESC"
        else:
            query += " ORDER BY p.created_at DESC"  # Default to latest
        
        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            cursor = await db.execute(query, params)
            posts = [dict(row) for row in await cursor.fetchall()]
            return posts
        except Exception as e:
            print(f"Database error: {str(e)}")
            return []

@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_posts(user_id: int, request: Request):
    """Get posts from a specific user."""
    # Extract token from request to check if user is authenticated
    token = await get_token_from_request(request)
    current_user = await get_current_user_optional(token) if token else None
    current_user_id = current_user["id"] if current_user else None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Build query with or without liked_by_user
        if current_user_id:
            query = """
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      (SELECT EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?)) as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = ?
                ORDER BY p.created_at DESC
            """
            cursor = await db.execute(query, (current_user_id, user_id))
        else:
            query = """
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      0 as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = ?
                ORDER BY p.created_at DESC
            """
            cursor = await db.execute(query, (user_id,))
        
        posts = [dict(row) for row in await cursor.fetchall()]
    
    return posts

@router.delete("/{post_id}")
async def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a post."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if the post exists and belongs to the user
        cursor = await db.execute(
            "SELECT * FROM posts WHERE id = ? AND user_id = ?", 
            (post_id, current_user['id'])
        )
        post = await cursor.fetchone()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or you don't have permission to delete it"
            )
        
        # Delete all likes for this post
        await db.execute("DELETE FROM likes WHERE post_id = ?", (post_id,))
        
        # Delete the post
        await db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        await db.commit()
    
    return {"message": "Post deleted successfully"}

@router.post("/search")
async def search_posts(search_term: str, request: Request):
    """Search for posts by prompt or caption."""
    search_pattern = f"%{search_term}%"
    
    # Extract token from request to check if user is authenticated
    token = await get_token_from_request(request)
    current_user = await get_current_user_optional(token) if token else None
    current_user_id = current_user["id"] if current_user else None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Build query with or without liked_by_user
        if current_user_id:
            query = """
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      (SELECT EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?)) as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.prompt LIKE ? OR p.caption LIKE ?
                ORDER BY p.created_at DESC
                LIMIT 50
            """
            cursor = await db.execute(query, (current_user_id, search_pattern, search_pattern))
        else:
            query = """
                SELECT p.*, u.username, 
                      (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as like_count,
                      0 as liked_by_user
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.prompt LIKE ? OR p.caption LIKE ?
                ORDER BY p.created_at DESC
                LIMIT 50
            """
            cursor = await db.execute(query, (search_pattern, search_pattern))
        
        posts = [dict(row) for row in await cursor.fetchall()]
    
    return posts

@router.post("/generate-preview")
async def generate_preview(post_data: PostCreate, current_user: dict = Depends(get_current_user)):
    """Generate an image preview without saving it as a post."""
    try:
        prompt = post_data.prompt.strip()
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt cannot be empty"
            )
            
        response = await together_client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=1024,  # Reduced size for faster generation
            height=1024,
            steps=4,
            n=1,
            response_format="b64_json",
            stop=[]
        )
        
        if not hasattr(response, 'data') or not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No image data received from API"
            )
            
        image_data = response.data[0].b64_json
        
        return {
            "success": True,
            "image_data": image_data,
            "prompt": post_data.prompt
        }
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating image: {str(e)}"
        )