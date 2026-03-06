from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ImageResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    total: int
    images: list[ImageResponse]
