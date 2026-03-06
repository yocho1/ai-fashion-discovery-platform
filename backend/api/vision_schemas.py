from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class VisionAnalysisResponse(BaseModel):
    """Response model for a single vision analysis."""

    id: int
    image_id: int
    clothing_type: Optional[str] = None
    categories: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    overall_confidence: Optional[float] = None
    analysis_status: str = "pending"
    model_used: str = "openrouter-vision"
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "image_id": 42,
                "clothing_type": "jacket",
                "categories": ["outerwear", "casual"],
                "attributes": {
                    "colors": ["navy blue"],
                    "patterns": ["solid"],
                    "materials": ["cotton blend"],
                    "style": ["casual", "sporty"],
                },
                "overall_confidence": 0.95,
                "analysis_status": "completed",
                "model_used": "openrouter-vision",
                "created_at": "2026-03-05T10:30:00",
                "updated_at": "2026-03-05T10:30:30",
            }
        }


class VisionAnalysisListResponse(BaseModel):
    """Response model for list of vision analyses."""

    total: int = Field(..., description="Total number of analyses for user")
    analyses: List[VisionAnalysisResponse] = Field(..., description="List of analyses")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 5,
                "analyses": [
                    {
                        "id": 1,
                        "image_id": 42,
                        "clothing_type": "jacket",
                        "categories": ["outerwear"],
                        "attributes": {"colors": ["navy"]},
                        "overall_confidence": 0.95,
                        "analysis_status": "completed",
                        "model_used": "openrouter-vision",
                        "created_at": "2026-03-05T10:30:00",
                        "updated_at": "2026-03-05T10:30:30",
                    }
                ],
            }
        }


class AnalysisStartRequest(BaseModel):
    """Request to start analysis on an image."""

    image_id: int = Field(..., description="ID of the image to analyze")

    class Config:
        json_schema_extra = {"example": {"image_id": 42}}


class AnalysisStartResponse(BaseModel):
    """Response when analysis is queued."""

    message: str = "Analysis started"
    analysis_id: int
    status: str = "pending"
    image_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Analysis started",
                "analysis_id": 1,
                "status": "pending",
                "image_id": 42,
            }
        }
