import json
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

    img = PILImage.new("RGB", (500, 500), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def test_start_analysis_unauthorized(test_client):
    """Test analysis endpoint without token."""
    response = test_client.post(
        "/vision/analyze",
        json={"image_id": 1},
    )
    assert response.status_code == 401


def test_start_analysis_image_not_found(test_client, db_session):
    """Test analyzing non-existent image."""
    user = AuthService.register_user(
        db_session, email="analyzer@test.com", username="analyzer", password="password123"
    )
    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.post(
        "/vision/analyze",
        json={"image_id": 999},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_start_analysis_success(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful analysis start."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    user = AuthService.register_user(
        db_session, email="analyzer@test.com", username="analyzer", password="password123"
    )
    
    # Create image
    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    mock_response = {
        "clothing_type": "jacket",
        "categories": ["casual"],
        "confidence": 0.94,
    }

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        response = test_client.post(
            "/vision/analyze",
            json={"image_id": image.id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Analysis started"
    assert data["image_id"] == image.id
    assert data["status"] == "completed"


def test_get_analysis_unauthorized(test_client):
    """Test get analysis without token."""
    response = test_client.get("/vision/analyses/1")
    assert response.status_code == 401


def test_get_analysis_not_found(test_client, db_session):
    """Test getting non-existent analysis."""
    user = AuthService.register_user(
        db_session, email="getter@test.com", username="getter", password="password123"
    )
    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.get(
        "/vision/analyses/999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_get_analysis_success(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successfully retrieving analysis results."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    user = AuthService.register_user(
        db_session, email="getter@test.com", username="getter", password="password123"
    )

    image = ImageService.save_image(
        db_session,
        user_id=user.id,
        file_content=sample_image_bytes,
        original_filename="test.jpg",
        mime_type="image/jpeg",
    )

    mock_response = {
        "clothing_type": "jacket",
        "categories": ["outerwear", "casual"],
        "attributes": {"colors": ["navy"], "style": ["sporty"]},
        "confidence": 0.96,
    }

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        VisionService.analyze_image(db_session, image.id)

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.get(
        f"/vision/analyses/{image.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["clothing_type"] == "jacket"
    assert "outerwear" in data["categories"]
    assert data["overall_confidence"] == 0.96


def test_list_user_analyses(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test listing user's analyses."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    user = AuthService.register_user(
        db_session, email="lister@test.com", username="lister", password="password123"
    )

    # Create multiple images with analyses
    mock_response = {"clothing_type": "shirt", "confidence": 0.92}

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        for i in range(3):
            image = ImageService.save_image(
                db_session,
                user_id=user.id,
                file_content=sample_image_bytes,
                original_filename=f"test_{i}.jpg",
                mime_type="image/jpeg",
            )
            VisionService.analyze_image(db_session, image.id)

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    response = test_client.get(
        "/vision/my-analyses",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["analyses"]) == 3


def test_list_user_analyses_pagination(test_client, db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test pagination in analysis listing."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    user = AuthService.register_user(
        db_session, email="paginator@test.com", username="paginator", password="password123"
    )

    mock_response = {"clothing_type": "pants", "confidence": 0.90}

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        for i in range(5):
            image = ImageService.save_image(
                db_session,
                user_id=user.id,
                file_content=sample_image_bytes,
                original_filename=f"test_{i}.jpg",
                mime_type="image/jpeg",
            )
            VisionService.analyze_image(db_session, image.id)

    token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})

    # First page
    response = test_client.get(
        "/vision/my-analyses?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["analyses"]) == 2

    # Second page
    response = test_client.get(
        "/vision/my-analyses?limit=2&offset=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert len(data["analyses"]) == 2
