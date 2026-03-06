from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ClothingItemResponse(BaseModel):
    """Response model for a clothing item."""

    id: int
    image_id: int
    user_id: int
    clothing_type: str
    categories: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    visibility: str
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "image_id": 42,
                "user_id": 1,
                "clothing_type": "jacket",
                "categories": ["outerwear", "casual"],
                "attributes": {"colors": ["navy"], "style": ["sporty"]},
                "visibility": "private",
                "created_at": "2026-03-05T10:30:00",
            }
        }


class OutfitItemInfo(BaseModel):
    """Info about a single item in an outfit."""

    id: int
    image_id: int
    clothing_type: str


class OutfitRecommendation(BaseModel):
    """A recommended outfit combination."""

    items: List[OutfitItemInfo] = Field(..., description="Items in this outfit")
    compatibility_score: float = Field(..., description="Score 0-1, how well items go together")
    suggestion: str = Field(..., description="Human-readable suggestion")


class GetRecommendationsRequest(BaseModel):
    """Request for outfit recommendations."""

    reference_image_id: int = Field(..., description="Base image for recommendations")
    limit: int = Field(5, ge=1, le=20, description="Max recommendations to return")

    class Config:
        json_schema_extra = {"example": {"reference_image_id": 42, "limit": 5}}


class CreateClothingItemRequest(BaseModel):
    """Request to create a clothing item from an analyzed image."""

    image_id: int = Field(..., description="Image ID to convert into a clothing item")
    visibility: str = Field("private", pattern="^(private|public)$", description="Item visibility")

    class Config:
        json_schema_extra = {
            "example": {
                "image_id": 42,
                "visibility": "private",
            }
        }


class OutfitInfo(BaseModel):
    """Information about a saved outfit."""

    id: int
    name: str
    description: Optional[str] = None
    items: List[int] = Field(..., description="List of clothing item IDs")
    compatibility_score: Optional[float] = None
    tags: Optional[List[str]] = None
    created_at: str


class SaveOutfitRequest(BaseModel):
    """Request to save an outfit."""

    name: str = Field(..., min_length=1, max_length=255, description="Outfit name")
    item_ids: List[int] = Field(..., min_items=2, max_items=5, description="Item IDs in outfit")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    tags: Optional[List[str]] = Field(None, description="Optional tags (season, occasion, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Casual Weekend Look",
                "item_ids": [1, 3, 5],
                "description": "Perfect for casual weekend outings",
                "tags": ["casual", "spring"],
            }
        }


class SaveOutfitResponse(BaseModel):
    """Response after saving an outfit."""

    message: str = "Outfit saved"
    outfit_id: int
    compatibility_score: float

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Outfit saved",
                "outfit_id": 10,
                "compatibility_score": 0.87,
            }
        }


class OutfitListResponse(BaseModel):
    """Response for list of outfits."""

    total: int = Field(..., description="Total outfits for user")
    outfits: List[OutfitInfo] = Field(..., description="List of outfits")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 3,
                "outfits": [
                    {
                        "id": 1,
                        "name": "Casual Weekend",
                        "description": "Perfect for weekends",
                        "items": [1, 3, 5],
                        "compatibility_score": 0.87,
                        "tags": ["casual"],
                        "created_at": "2026-03-05T10:30:00",
                    }
                ],
            }
        }


class RecommendationsResponse(BaseModel):
    """Response with outfit recommendations."""

    total: int = Field(..., description="Number of recommendations")
    recommendations: List[OutfitRecommendation] = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "recommendations": [
                    {
                        "items": [
                            {"id": 1, "image_id": 42, "clothing_type": "jacket"},
                            {"id": 2, "image_id": 43, "clothing_type": "pants"},
                        ],
                        "compatibility_score": 0.92,
                        "suggestion": "Pair jacket with pants",
                    }
                ],
            }
        }


class ClothingItemListResponse(BaseModel):
    """Response for list of clothing items."""

    total: int = Field(..., description="Total items for user")
    items: List[ClothingItemResponse] = Field(..., description="List of clothing items")
