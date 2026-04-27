from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    telegram_user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- COMPLAINT SCHEMAS ---
class ComplaintCreate(BaseModel):
    telegram_user_id: str
    category: Optional[str] = None
    description: Optional[str] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None

class ComplaintResponse(BaseModel):
    id: int
    ghmc_id: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- MEDIA SCHEMAS ---
class MediaCreate(BaseModel):
    telegram_user_id: str
    complaint_id: Optional[int] = None
    media_type: str
    file_path: str
