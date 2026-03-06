import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.recommendation_schemas import (
    RecommendationsResponse,
    OutfitRecommendation,
    OutfitItemInfo,
    SaveOutfitRequest,
    SaveOutfitResponse,
    OutfitListResponse,
    OutfitInfo,
    ClothingItemListResponse,
    ClothingItemResponse,
    CreateClothingItemRequest,
    GetRecommendationsRequest,
)
from db.models import Image
from db.session import get_db_session
from services.auth_service import AuthService
from services.recommendation_service import RecommendationService

router = APIRouter(tags=["recommendations"])


async def get_current_user_from_token(authorization: str | None = Query(default=None), db: Session = Depends(get_db_session)):
    """Extract user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    payload = AuthService.verify_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("user_id")
    user = AuthService.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.post("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    request: GetRecommendationsRequest,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Get outfit recommendations based on a reference image."""
    user = await get_current_user_from_token(authorization, db)

    # Verify reference image belongs to user
    image = db.query(Image).filter(
        Image.id == request.reference_image_id, Image.user_id == user.id
    ).first()

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found")

    recommendations = RecommendationService.get_recommendations(
        db, user.id, request.reference_image_id, limit=request.limit
    )

    return RecommendationsResponse(
        total=len(recommendations),
        recommendations=[
            OutfitRecommendation(
                items=[
                    OutfitItemInfo(
                        id=item["id"],
                        image_id=item["image_id"],
                        clothing_type=item["clothing_type"],
                    )
                    for item in rec["items"]
                ],
                compatibility_score=rec["compatibility_score"],
                suggestion=rec["suggestion"],
            )
            for rec in recommendations
        ],
    )


@router.post("/clothing-items", response_model=ClothingItemResponse, status_code=status.HTTP_201_CREATED)
async def create_clothing_item(
    request: CreateClothingItemRequest,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Create a clothing item from an analyzed image."""
    user = await get_current_user_from_token(authorization, db)

    image = db.query(Image).filter(
        Image.id == request.image_id, Image.user_id == user.id
    ).first()

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    item = RecommendationService.create_clothing_item(
        db,
        image_id=request.image_id,
        user_id=user.id,
        visibility=request.visibility,
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create clothing item - ensure analysis is completed",
        )

    return ClothingItemResponse(
        id=item.id,
        image_id=item.image_id,
        user_id=item.user_id,
        clothing_type=item.clothing_type,
        categories=json.loads(item.categories) if item.categories else None,
        attributes=json.loads(item.attributes) if item.attributes else None,
        visibility=item.visibility,
        created_at=item.created_at.isoformat(),
    )


@router.post("/outfits", response_model=SaveOutfitResponse, status_code=status.HTTP_201_CREATED)
async def save_outfit(
    request: SaveOutfitRequest,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Save an outfit combination."""
    user = await get_current_user_from_token(authorization, db)

    outfit = RecommendationService.save_outfit(
        db,
        user_id=user.id,
        name=request.name,
        item_ids=request.item_ids,
        description=request.description,
        tags=request.tags,
    )

    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save outfit - verify items belong to you and count",
        )

    return SaveOutfitResponse(
        message="Outfit saved",
        outfit_id=outfit.id,
        compatibility_score=outfit.compatibility_score or 0.5,
    )


@router.get("/outfits", response_model=OutfitListResponse)
async def list_user_outfits(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Get all saved outfits for current user."""
    user = await get_current_user_from_token(authorization, db)

    outfits, total = RecommendationService.get_user_outfits(db, user.id, limit=limit, offset=offset)

    return OutfitListResponse(
        total=total,
        outfits=[
            OutfitInfo(
                id=outfit.id,
                name=outfit.name,
                description=outfit.description,
                items=json.loads(outfit.items),
                compatibility_score=outfit.compatibility_score,
                tags=json.loads(outfit.tags) if outfit.tags else None,
                created_at=outfit.created_at.isoformat(),
            )
            for outfit in outfits
        ],
    )


@router.delete("/outfits/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: int,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Delete an outfit."""
    user = await get_current_user_from_token(authorization, db)

    if not RecommendationService.delete_outfit(db, outfit_id, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")

    return None


@router.get("/clothing-items", response_model=ClothingItemListResponse)
async def list_user_clothing_items(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Get all clothing items for current user."""
    user = await get_current_user_from_token(authorization, db)

    items, total = RecommendationService.get_user_clothing_items(
        db, user.id, limit=limit, offset=offset
    )

    return ClothingItemListResponse(
        total=total,
        items=[
            ClothingItemResponse(
                id=item.id,
                image_id=item.image_id,
                user_id=item.user_id,
                clothing_type=item.clothing_type,
                categories=json.loads(item.categories) if item.categories else None,
                attributes=json.loads(item.attributes) if item.attributes else None,
                visibility=item.visibility,
                created_at=item.created_at.isoformat(),
            )
            for item in items
        ],
    )

