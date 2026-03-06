import json
from unittest.mock import patch, MagicMock

import pytest

from services.vision_service import VisionService
from db.models import Image, VisionAnalysis


@pytest.fixture
def sample_image(db_session):
    """Create a sample image for testing."""
    image = Image(
        user_id=1,
        filename="test_jacket.jpg",
        original_filename="jacket.jpg",
        file_path="./uploads/test_jacket.jpg",
        file_size=50000,
        mime_type="image/jpeg",
        width=500,
        height=500,
        description="Blue jacket",
    )
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)
    return image


def test_get_analysis_not_found(db_session):
    """Test getting analysis for non-existent image."""
    analysis = VisionService.get_analysis(db_session, image_id=999)
    assert analysis is None


def test_get_user_analyses_empty(db_session):
    """Test getting analyses for user with no images."""
    analyses, total = VisionService.get_user_analyses(db_session, user_id=999)
    assert total == 0
    assert len(analyses) == 0


def test_analyze_image_not_found(db_session):
    """Test analyzing non-existent image."""
    analysis = VisionService.analyze_image(db_session, image_id=999)
    assert analysis is None


def test_analyze_image_no_api_key(db_session, sample_image, monkeypatch):
    """Test analysis fails without API key."""
    from core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", None)

    with pytest.raises(ValueError, match="API key not configured"):
        VisionService.analyze_image(db_session, sample_image.id)


def test_analyze_image_success(db_session, sample_image, monkeypatch, tmp_path):
    """Test successful image analysis."""
    from core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")
    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Save a test file
    test_file = tmp_path / "test_jacket.jpg"
    test_file.write_bytes(b"fake image data")
    monkeypatch.setattr(sample_image, "file_path", str(test_file))

    # Mock OpenRouter API response
    mock_response = {
        "clothing_type": "jacket",
        "categories": ["outerwear", "casual"],
        "attributes": {
            "colors": ["navy blue"],
            "patterns": ["solid"],
            "materials": ["cotton blend"],
            "style": ["sporty"],
        },
        "confidence": 0.95,
        "description": "Navy blue casual jacket",
    }

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        analysis = VisionService.analyze_image(db_session, sample_image.id)

    assert analysis is not None
    assert analysis.image_id == sample_image.id
    assert analysis.clothing_type == "jacket"
    assert analysis.analysis_status == "completed"
    assert analysis.overall_confidence == 0.95

    # Verify JSON fields
    categories = json.loads(analysis.categories)
    assert "outerwear" in categories
    attributes = json.loads(analysis.attributes)
    assert attributes["colors"][0] == "navy blue"


def test_analyze_image_api_failure(db_session, sample_image, monkeypatch, tmp_path):
    """Test analysis handles API failure gracefully."""
    from core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")
    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    test_file = tmp_path / "test_jacket.jpg"
    test_file.write_bytes(b"fake image data")
    monkeypatch.setattr(sample_image, "file_path", str(test_file))

    with patch.object(VisionService, "_call_openrouter_api", return_value=None):
        analysis = VisionService.analyze_image(db_session, sample_image.id)

    assert analysis is not None
    assert analysis.analysis_status == "failed"
    assert analysis.error_message == "Failed to parse API response"


def test_analyze_image_exception_handling(db_session, sample_image, monkeypatch):
    """Test analysis handles exceptions gracefully."""
    from core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")

    # Simulate file read error
    with patch("services.storage_service.StorageService.get_file", side_effect=Exception("File not found")):
        analysis = VisionService.analyze_image(db_session, sample_image.id)

    assert analysis is not None
    assert analysis.analysis_status == "failed"
    assert "File not found" in analysis.error_message


def test_analyze_image_duplicate_analysis(db_session, sample_image, monkeypatch, tmp_path):
    """Test that duplicate analyses return the existing one."""
    from core.config import settings
    from services.auth_service import AuthService
    from db.models import Image

    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")
    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Create test file first
    test_file = tmp_path / "test_jacket.jpg"
    test_file.write_bytes(b"fake image data")

    # Update sample_image to have the correct file path
    sample_image.file_path = str(test_file)
    db_session.commit()

    # Create first analysis
    mock_response = {"clothing_type": "jacket", "confidence": 0.95}
    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        analysis1 = VisionService.analyze_image(db_session, sample_image.id)

    # Attempt second analysis should return the same record
    with patch.object(VisionService, "_call_openrouter_api") as mock_api:
        analysis2 = VisionService.analyze_image(db_session, sample_image.id)
        mock_api.assert_not_called()  # API should not be called

    assert analysis1.id == analysis2.id
    assert analysis2.analysis_status == "completed"


def test_get_user_analyses_pagination(db_session, tmp_path, monkeypatch):
    """Test paginated retrieval of user analyses."""
    from core.config import settings
    from services.auth_service import AuthService

    monkeypatch.setattr(settings, "openrouter_api_key", "test-api-key")
    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    # Create user and images
    user = AuthService.register_user(db_session, "analyzer@test.com", "analyzer", "password123")

    # Create multiple images and analyses
    mock_response = {"clothing_type": "jacket", "confidence": 0.9}
    
    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        for i in range(5):
            image = Image(
                user_id=user.id,
                filename=f"test_{i}.jpg",
                original_filename=f"image_{i}.jpg",
                file_path=f"./uploads/test_{i}.jpg",
                file_size=50000,
                mime_type="image/jpeg",
                width=500,
                height=500,
            )
            db_session.add(image)
            db_session.commit()
            VisionService.analyze_image(db_session, image.id)

    # Test pagination
    analyses, total = VisionService.get_user_analyses(db_session, user.id, limit=2, offset=0)
    assert total == 5
    assert len(analyses) == 2

    analyses2, _ = VisionService.get_user_analyses(db_session, user.id, limit=2, offset=2)
    assert len(analyses2) == 2


def test_call_openrouter_api_json_parsing(monkeypatch):
    """Test API response parsing with markdown code blocks."""
    from core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    # Mock httpx response with JSON in markdown
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```json\n{\"clothing_type\": \"shirt\", \"confidence\": 0.88}\n```"
                }
            }
        ]
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
        result = VisionService._call_openrouter_api("base64data", "image/jpeg")

    assert result is not None
    assert result["clothing_type"] == "shirt"
    assert result["confidence"] == 0.88


def test_call_openrouter_api_error_handling(monkeypatch):
    """Test API error handling."""
    from core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
        result = VisionService._call_openrouter_api("base64data", "image/jpeg")

    assert result is None
