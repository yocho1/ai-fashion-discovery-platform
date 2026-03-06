from unittest.mock import patch

import pytest

from services.auth_service import AuthService
from services.image_service import ImageService
from services.vision_service import VisionService


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    from PIL import Image as PILImage
    import io

    img = PILImage.new("RGB", (500, 500), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def test_create_clothing_item_unauthorized(test_client):
    """Test creating clothing item without token."""
    response = test_client.post(
        "/recommendations/clothing-items",
        json={"image_id": 1, "visibility": "private"},
    )
    assert response.status_code == 401


def test_create_clothing_item_image_not_found(test_client, db_session):
    """Test creating clothing item with non-existent image."""
    user = AuthService.register_user(
        db_session, email="creator@test.com", username="creator", password="password123"
    )
    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.post(
        "/recommendations/clothing-items",
        json={"image_id": 999, "visibility": "private"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "Image not found" in response.json()["detail"]


def test_create_clothing_item_image_not_owned_by_user(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test creating clothing item from image owned by another user."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Create two users
    user1 = AuthService.register_user(
        db_session, email="user1@test.com", username="user1", password="password123"
    )
    user2 = AuthService.register_user(
        db_session, email="user2@test.com", username="user2", password="password123"
    )

    # Create image for user1
    image = ImageService.save_image(
        db_session,
        user_id=user1.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    # Try to create clothing item as user2
    token = AuthService.create_access_token(data={"sub": user2.email, "user_id": user2.id})

    response = test_client.post(
        "/recommendations/clothing-items",
        json={"image_id": image.id, "visibility": "private"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "Image not found" in response.json()["detail"]


def test_create_clothing_item_analysis_not_completed(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test creating clothing item when analysis is not completed."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    user = AuthService.register_user(
        db_session, email="analyzer@test.com", username="analyzer", password="password123"
    )

    # Create image without analysis
    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.post(
        "/recommendations/clothing-items",
        json={"image_id": image.id, "visibility": "private"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "ensure analysis is completed" in response.json()["detail"]


def test_create_clothing_item_success(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful clothing item creation from analyzed image."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    user = AuthService.register_user(
        db_session, email="analyzer@test.com", username="analyzer", password="password123"
    )

    # Create and analyze image
    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    mock_response = {
        "clothing_type": "jacket",
        "categories": ["casual", "outdoor"],
        "confidence": 0.94,
        "color": "blue",
        "material": "cotton",
    }

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        # Analyze the image
        test_client.post(
            "/vision/analyze",
            json={"image_id": image.id},
            headers={"Authorization": f"Bearer {token}"},
        )

    # Now create clothing item from analyzed image
    response = test_client.post(
        "/recommendations/clothing-items",
        json={"image_id": image.id, "visibility": "public"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["image_id"] == image.id
    assert data["user_id"] == user.id
    assert data["clothing_type"] == "jacket"
    assert data["visibility"] == "public"
    assert data["categories"] == ["casual", "outdoor"]
    assert data["attributes"]["color"] == "blue"
    assert data["attributes"]["material"] == "cotton"
    assert data["created_at"]


def test_create_clothing_item_private_visibility(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test creating clothing item with private visibility."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    user = AuthService.register_user(
        db_session, email="privuser@test.com", username="privuser", password="password123"
    )

    # Create and analyze image
    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    mock_response = {
        "clothing_type": "shirt",
        "categories": ["casual"],
        "confidence": 0.85,
    }

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        test_client.post(
            "/vision/analyze",
            json={"image_id": image.id},
            headers={"Authorization": f"Bearer {token}"},
        )

    # Create as private
    response = test_client.post(
        "/recommendations/clothing-items",
        json={"image_id": image.id, "visibility": "private"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["visibility"] == "private"


def test_get_recommendations_unauthorized(test_client):
    """Test getting recommendations without token."""
    response = test_client.post(
        "/recommendations/recommendations",
        json={"reference_image_id": 1, "limit": 5},
    )
    assert response.status_code == 401


def test_get_recommendations_image_not_found(test_client, db_session):
    """Test getting recommendations for non-existent image."""
    user = AuthService.register_user(
        db_session, email="rec_user@test.com", username="rec_user", password="password123"
    )
    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.post(
        "/recommendations/recommendations",
        json={"reference_image_id": 999, "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "Reference image not found" in response.json()["detail"]


def test_get_recommendations_success(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful recommendation retrieval."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    user = AuthService.register_user(
        db_session, email="rec_user@test.com", username="rec_user", password="password123"
    )

    # Create reference image
    ref_image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="ref.jpg",
        mime_type="image/jpeg",
    )

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.post(
        "/recommendations/recommendations",
        json={"reference_image_id": ref_image.id, "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
