from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    bio: Optional[str] = None

class User(UserBase):
    id: int
    bio: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode

class UserProfile(User):
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    is_following: bool = False

class PostBase(BaseModel):
    prompt: str
    caption: Optional[str] = None

class PostCreate(PostBase):
    pass

class Post(PostBase):
    id: int
    user_id: int
    image_data: str
    created_at: datetime
    like_count: int = 0
    liked_by_user: bool = False
    username: Optional[str] = None
    
    class Config:
        from_attributes = True  # Updated from orm_mode

class PostResponse(BaseModel):
    id: int
    user_id: int
    prompt: str
    caption: Optional[str] = None
    created_at: datetime
    like_count: int = 0
    liked_by_user: bool = False
    username: str
    
    class Config:
        from_attributes = True  # Updated from orm_mode

class PostList(BaseModel):
    posts: List[PostResponse]
    
    class Config:
        from_attributes = True  # Updated from orm_mode

class FollowCreate(BaseModel):
    user_id: int

class LikeCreate(BaseModel):
    post_id: int

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class SearchQuery(BaseModel):
    query: str

class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20