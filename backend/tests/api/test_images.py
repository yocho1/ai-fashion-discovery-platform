import io

import pytest
from PIL import Image as PILImage


@pytest.fixture
def sample_image_bytes():
    """Create a sample image for testing."""
    img = PILImage.new("RGB", (500, 500), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def test_upload_image_success(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful image upload."""
    from core.config import settings
    from services.auth_service import AuthService

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Register and login user
    user = AuthService.register_user(
        db_session, email="uploader@example.com", username="uploader", password="password123"
    )
    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    # Upload image
    response = test_client.post(
        "/images/upload",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        params={"description": "Test upload"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] is not None
    assert data["original_filename"] == "test.jpg"
    assert data["file_size"] == len(sample_image_bytes)
    assert data["width"] == 500
    assert data["height"] == 500


def test_upload_image_unauthorized(test_client, sample_image_bytes):
    """Test upload without authentication."""
    response = test_client.post(
        "/images/upload",
        files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
    )

    assert response.status_code == 401


def test_list_user_images(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test listing user images."""
    from core.config import settings
    from services.auth_service import AuthService
    from services.image_service import ImageService

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Create user and images
    user = AuthService.register_user(
        db_session, email="lister@example.com", username="lister", password="password123"
    )

    for i in range(3):
        ImageService.save_image(
            db_session,
            user_id=user.id,
            file_content=sample_image_bytes,
            original_filename=f"test{i}.jpg",
            mime_type="image/jpeg",
        )

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    # List images
    response = test_client.get("/images/my-images", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["images"]) == 3


def test_get_image_metadata(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test retrieving image metadata."""
    from core.config import settings
    from services.auth_service import AuthService
    from services.image_service import ImageService

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Create user and image
    user = AuthService.register_user(
        db_session, email="getter@example.com", username="getter", password="password123"
    )

    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    # Get image metadata
    response = test_client.get(f"/images/{image.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == image.id
    assert data["original_filename"] == "test.jpg"


def test_delete_image(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test deleting an image."""
    from core.config import settings
    from services.auth_service import AuthService
    from services.image_service import ImageService

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Create user and image
    user = AuthService.register_user(
        db_session, email="deleter@example.com", username="deleter", password="password123"
    )

    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    # Delete image
    response = test_client.delete(f"/images/{image.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204

    # Verify deletion
    response = test_client.get(f"/images/{image.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
