from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.image_schemas import ImageResponse, ImageListResponse, ImageUploadResponse
from db.session import get_db_session
from services.image_service import ImageService
from services.auth_service import AuthService

router = APIRouter(tags=["images"])


def get_user_from_authorization(authorization: str | None = Query(default=None), db: Session = Depends(get_db_session)):
    """Helper to extract and authenticate user from Authorization query parameter."""
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


@router.post("/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    description: str = Query(None, max_length=512),
    user = Depends(get_user_from_authorization),
    db: Session = Depends(get_db_session),
):
    """Upload and process an image."""
    # Read file
    file_content = await file.read()

    try:
        # Save image (validate, store, persist metadata)
        image = ImageService.save_image(
            db,
            user_id=user.id,
            file_content=file_content,
            original_filename=file.filename,
            mime_type=file.content_type,
            description=description,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ImageUploadResponse(
        id=image.id,
        filename=image.filename,
        original_filename=image.original_filename,
        file_size=image.file_size,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        description=image.description,
        created_at=image.created_at.isoformat(),
    )


@router.get("/my-images", response_model=ImageListResponse)
async def list_user_images(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user = Depends(get_user_from_authorization),
    db: Session = Depends(get_db_session),
):
    """Get all images uploaded by the current user."""
    images, total = ImageService.get_user_images(db, user.id, limit=limit, offset=offset)

    return ImageListResponse(
        total=total,
        images=[
            ImageResponse(
                id=img.id,
                user_id=img.user_id,
                filename=img.filename,
                original_filename=img.original_filename,
                file_size=img.file_size,
                mime_type=img.mime_type,
                width=img.width,
                height=img.height,
                description=img.description,
                created_at=img.created_at.isoformat(),
                updated_at=img.updated_at.isoformat(),
            )
            for img in images
        ],
    )


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: int,
    user = Depends(get_user_from_authorization),
    db: Session = Depends(get_db_session),
):
    """Get a specific image metadata."""
    image = ImageService.get_image_by_id(db, image_id, user.id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    return ImageResponse(
        id=image.id,
        user_id=image.user_id,
        filename=image.filename,
        original_filename=image.original_filename,
        file_size=image.file_size,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        description=image.description,
        created_at=image.created_at.isoformat(),
        updated_at=image.updated_at.isoformat(),
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    user = Depends(get_user_from_authorization),
    db: Session = Depends(get_db_session),
):
    """Delete an image."""
    if not ImageService.delete_image(db, image_id, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    return None


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: int,
    user = Depends(get_user_from_authorization),
    db: Session = Depends(get_db_session),
):
    """Serve an image file."""
    image = ImageService.get_image_by_id(db, image_id, user.id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    file_path = Path(image.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found on disk")

    return FileResponse(
        path=str(file_path.resolve()),
        media_type=image.mime_type,
        filename=image.original_filename,
    )
