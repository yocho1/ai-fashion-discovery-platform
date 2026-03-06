from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from api.vision_schemas import (
    VisionAnalysisResponse,
    VisionAnalysisListResponse,
    AnalysisStartRequest,
    AnalysisStartResponse,
)
from db.models import Image, VisionAnalysis
from db.session import get_db_session, SessionLocal
from services.vision_service import VisionService
from services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["vision"])


def run_vision_analysis_task(image_id: int):
    """Background task to run vision analysis with its own DB session."""
    db = SessionLocal()
    try:
        logger.info(f"Starting background vision analysis for image {image_id}")
        VisionService.analyze_image(db, image_id)
        logger.info(f"Completed background vision analysis for image {image_id}")
    except Exception as e:
        logger.error(f"Background vision analysis failed for image {image_id}: {str(e)}")
    finally:
        db.close()


# Dependency to get current user from token (reuse from images routes)
def get_current_user_from_token(authorization: str | None = Query(default=None), db: Session = Depends(get_db_session)):
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


@router.post("/analyze", response_model=AnalysisStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    request: AnalysisStartRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Start AI vision analysis on an uploaded image (non-blocking)."""
    user = get_current_user_from_token(authorization, db)

    # Verify image belongs to user
    image = db.query(Image).filter(
        Image.id == request.image_id, Image.user_id == user.id
    ).first()

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    try:
        # Check for existing analysis
        existing = db.query(VisionAnalysis).filter(VisionAnalysis.image_id == request.image_id).first()
        
        if existing and existing.analysis_status == "completed":
            # Already analyzed
            return AnalysisStartResponse(
                message="Analysis already completed",
                analysis_id=existing.id,
                status=existing.analysis_status,
                image_id=existing.image_id,
            )
        
        if not existing:
            # Create pending analysis record immediately
            analysis = VisionAnalysis(
                image_id=request.image_id,
                analysis_status="pending",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
        else:
            analysis = existing
        
        # Run analysis in background with its own session
        background_tasks.add_task(run_vision_analysis_task, request.image_id)
        
        return AnalysisStartResponse(
            message="Analysis started",
            analysis_id=analysis.id,
            status=analysis.analysis_status,
            image_id=analysis.image_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/analyses/{image_id}", response_model=VisionAnalysisResponse)
async def get_analysis(
    image_id: int,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Get vision analysis results for a specific image."""
    user = get_current_user_from_token(authorization, db)

    # Verify image belongs to user
    image = db.query(Image).filter(
        Image.id == image_id, Image.user_id == user.id
    ).first()

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    analysis = VisionService.get_analysis(db, image_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    # Parse JSON fields back to dicts
    import json

    categories = json.loads(analysis.categories) if analysis.categories else None
    attributes = json.loads(analysis.attributes) if analysis.attributes else None

    return VisionAnalysisResponse(
        id=analysis.id,
        image_id=analysis.image_id,
        clothing_type=analysis.clothing_type,
        categories=categories,
        attributes=attributes,
        overall_confidence=analysis.overall_confidence,
        analysis_status=analysis.analysis_status,
        model_used=analysis.model_used,
        created_at=analysis.created_at.isoformat(),
        updated_at=analysis.updated_at.isoformat(),
    )


@router.get("/my-analyses", response_model=VisionAnalysisListResponse)
async def list_user_analyses(
    limit: int = 50,
    offset: int = 0,
    authorization: str | None = Query(default=None),
    db: Session = Depends(get_db_session),
):
    """Get all vision analyses for the current user's images."""
    user = get_current_user_from_token(authorization, db)

    analyses, total = VisionService.get_user_analyses(db, user.id, limit=limit, offset=offset)

    import json

    return VisionAnalysisListResponse(
        total=total,
        analyses=[
            VisionAnalysisResponse(
                id=analysis.id,
                image_id=analysis.image_id,
                clothing_type=analysis.clothing_type,
                categories=json.loads(analysis.categories) if analysis.categories else None,
                attributes=json.loads(analysis.attributes) if analysis.attributes else None,
                overall_confidence=analysis.overall_confidence,
                analysis_status=analysis.analysis_status,
                model_used=analysis.model_used,
                created_at=analysis.created_at.isoformat(),
                updated_at=analysis.updated_at.isoformat(),
            )
            for analysis in analyses
        ],
    )
