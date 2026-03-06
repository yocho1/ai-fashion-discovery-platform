import io
from typing import Optional

from PIL import Image as PILImage
from sqlalchemy.orm import Session

from core.config import settings
from db.models import Image
from services.storage_service import StorageService


class ImageService:
    """Handle image validation and processing."""

    @staticmethod
    def validate_image(file_content: bytes, mime_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate image file.
        Returns: (is_valid, error_message)
        """
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.max_upload_size_mb:
            return False, f"File size exceeds {settings.max_upload_size_mb}MB limit"

        # Check MIME type
        if mime_type not in settings.allowed_image_types:
            return False, f"Unsupported image type: {mime_type}"

        # Validate image format and dimensions
        try:
            image = PILImage.open(io.BytesIO(file_content))
            width, height = image.size

            if width < settings.min_image_dimension or height < settings.min_image_dimension:
                return False, f"Image dimensions must be at least {settings.min_image_dimension}x{settings.min_image_dimension}"

            # Convert to RGB if necessary (for PNG with transparency, etc.)
            if image.mode != "RGB":
                image = image.convert("RGB")

            return True, None
        except Exception as e:
            return False, f"Invalid image format: {str(e)}"

    @staticmethod
    def get_image_dimensions(file_content: bytes) -> tuple[Optional[int], Optional[int]]:
        """Get image dimensions."""
        try:
            image = PILImage.open(io.BytesIO(file_content))
            return image.size
        except Exception:
            return None, None

    @staticmethod
    def save_image(
        session: Session,
        user_id: int,
        file_content: bytes,
        original_filename: str,
        mime_type: str,
        description: Optional[str] = None,
    ) -> Optional[Image]:
        """
        Validate, save, and persist image metadata.
        """
        # Validate image
        is_valid, error_msg = ImageService.validate_image(file_content, mime_type)
        if not is_valid:
            raise ValueError(error_msg)

        # Get dimensions
        width, height = ImageService.get_image_dimensions(file_content)

        # Save file
        filename, file_path = StorageService.save_file(file_content, user_id, original_filename)

        # Save metadata to DB
        image = Image(
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=len(file_content),
            mime_type=mime_type,
            width=width,
            height=height,
            description=description,
        )
        session.add(image)
        session.commit()
        session.refresh(image)

        return image

    @staticmethod
    def get_user_images(session: Session, user_id: int, limit: int = 50, offset: int = 0) -> tuple[list[Image], int]:
        """Get all images for a user."""
        query = session.query(Image).filter(Image.user_id == user_id)
        total = query.count()
        images = query.order_by(Image.created_at.desc()).limit(limit).offset(offset).all()
        return images, total

    @staticmethod
    def get_image_by_id(session: Session, image_id: int, user_id: int) -> Optional[Image]:
        """Get a specific image (ensure user owns it)."""
        return session.query(Image).filter(Image.id == image_id, Image.user_id == user_id).first()

    @staticmethod
    def delete_image(session: Session, image_id: int, user_id: int) -> bool:
        """Delete an image."""
        image = ImageService.get_image_by_id(session, image_id, user_id)
        if not image:
            return False

        # Delete file from storage
        StorageService.delete_file(image.file_path)

        # Delete from DB
        session.delete(image)
        session.commit()

        return True
