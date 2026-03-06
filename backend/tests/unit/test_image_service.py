import io
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image as PILImage

from services.image_service import ImageService
from services.storage_service import StorageService


@pytest.fixture
def sample_image_bytes():
    """Create a sample image for testing."""
    img = PILImage.new("RGB", (500, 500), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


@pytest.fixture
def small_image_bytes():
    """Create a small image that fails validation."""
    img = PILImage.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def test_validate_image_success(sample_image_bytes):
    """Test successful image validation."""
    is_valid, error_msg = ImageService.validate_image(sample_image_bytes, "image/jpeg")
    assert is_valid is True
    assert error_msg is None


def test_validate_image_too_small(small_image_bytes):
    """Test validation with too-small image."""
    is_valid, error_msg = ImageService.validate_image(small_image_bytes, "image/jpeg")
    assert is_valid is False
    assert "dimensions" in error_msg.lower()


def test_validate_image_unsupported_type(sample_image_bytes):
    """Test validation with unsupported MIME type."""
    is_valid, error_msg = ImageService.validate_image(sample_image_bytes, "image/bmp")
    assert is_valid is False
    assert "unsupported" in error_msg.lower()


def test_validate_image_too_large():
    """Test validation with oversized image."""
    # Create large dummy data > 10MB
    large_data = b"x" * (11 * 1024 * 1024)
    is_valid, error_msg = ImageService.validate_image(large_data, "image/jpeg")
    assert is_valid is False
    assert "exceeds" in error_msg.lower()


def test_get_image_dimensions(sample_image_bytes):
    """Test getting image dimensions."""
    width, height = ImageService.get_image_dimensions(sample_image_bytes)
    assert width == 500
    assert height == 500


def test_get_image_dimensions_invalid():
    """Test getting dimensions of invalid data."""
    width, height = ImageService.get_image_dimensions(b"not an image")
    assert width is None
    assert height is None


def test_save_image_success(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test saving an image successfully."""
    from core.config import settings

    # Mock storage path
    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    image = ImageService.save_image(
        db_session,
        user_id=1,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
        description="Test image",
    )

    assert image.id is not None
    assert image.user_id == 1
    assert image.filename is not None
    assert image.file_size == len(sample_image_bytes)
    assert image.width == 500
    assert image.height == 500
    assert image.description == "Test image"


def test_save_image_invalid(db_session, small_image_bytes, monkeypatch):
    """Test saving an invalid image."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", "./uploads")

    with pytest.raises(ValueError, match="dimensions"):
        ImageService.save_image(
            db_session,
            user_id=1,
            file_content=small_image_bytes,
            original_filename="small.jpg",
            mime_type="image/jpeg",
        )


def test_get_user_images(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test retrieving user images."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Save multiple images
    for i in range(3):
        ImageService.save_image(
            db_session,
            user_id=1,
            file_content=sample_image_bytes,
            original_filename=f"test{i}.jpg",
            mime_type="image/jpeg",
        )

    images, total = ImageService.get_user_images(db_session, user_id=1)

    assert total == 3
    assert len(images) == 3


def test_get_image_by_id(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test retrieving a specific image."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    image = ImageService.save_image(
        db_session,
        user_id=1,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    retrieved = ImageService.get_image_by_id(db_session, image.id, user_id=1)

    assert retrieved is not None
    assert retrieved.id == image.id


def test_get_image_by_id_wrong_user(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test that users can't access other users' images."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    image = ImageService.save_image(
        db_session,
        user_id=1,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    retrieved = ImageService.get_image_by_id(db_session, image.id, user_id=2)

    assert retrieved is None


def test_delete_image(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test deleting an image."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    image = ImageService.save_image(
        db_session,
        user_id=1,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    result = ImageService.delete_image(db_session, image.id, user_id=1)

    assert result is True

    # Verify it's deleted
    retrieved = ImageService.get_image_by_id(db_session, image.id, user_id=1)
    assert retrieved is None
