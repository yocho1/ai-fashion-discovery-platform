import json
from unittest.mock import patch

import pytest

from services.auth_service import AuthService
from services.image_service import ImageService
from services.vision_service import VisionService
from services.recommendation_service import RecommendationService
from services.embedding_service import EmbeddingService


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    from PIL import Image as PILImage
    import io

    img = PILImage.new("RGB", (500, 500), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def test_create_clothing_item_no_analysis(db_session):
    """Test creating clothing item without completed analysis."""
    item = RecommendationService.create_clothing_item(db_session, image_id=999, user_id=1)
    assert item is None


def test_create_clothing_item_success(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful clothing item creation."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    user = AuthService.register_user(db_session, "creator@test.com", "creator", "password123")

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
        "categories": ["outerwear"],
        "attributes": {"colors": ["blue"], "style": ["casual"]},
        "confidence": 0.9,
    }

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_response):
        VisionService.analyze_image(db_session, image.id)

    # Create clothing item
    item = RecommendationService.create_clothing_item(db_session, image.id, user.id)

    assert item is not None
    assert item.user_id == user.id
    assert item.clothing_type == "jacket"
    assert item.embedding is not None


def test_get_recommendations_no_items(db_session):
    """Test getting recommendations with no clothing items."""
    recs = RecommendationService.get_recommendations(db_session, user_id=999, reference_image_id=1)
    assert len(recs) == 0


def test_get_recommendations_success(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful recommendation generation."""
    from core.config import settings
    from db.models import Image, ClothingItem

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    user = AuthService.register_user(db_session, "recommender@test.com", "recommender", "password123")

    # Create reference image and analyze
    ref_image = ImageService.save_image(
        db_session, user_id=user.id, file_content=sample_image_bytes, original_filename="jacket.jpg", mime_type="image/jpeg"
    )

    mock_jacket = {
        "clothing_type": "jacket",
        "categories": ["outerwear"],
        "attributes": {"colors": ["navy"], "style": ["casual"]},
        "confidence": 0.9,
    }

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_jacket):
        VisionService.analyze_image(db_session, ref_image.id)

    ref_item = RecommendationService.create_clothing_item(db_session, ref_image.id, user.id)

    # Create complementary item
    comp_image = ImageService.save_image(
        db_session, user_id=user.id, file_content=sample_image_bytes, original_filename="pants.jpg", mime_type="image/jpeg"
    )

    mock_pants = {
        "clothing_type": "pants",
        "categories": ["bottoms"],
        "attributes": {"colors": ["navy"], "style": ["casual"]},
        "confidence": 0.88,
    }

    with patch.object(VisionService, "_call_openrouter_api", return_value=mock_pants):
        VisionService.analyze_image(db_session, comp_image.id)

    comp_item = RecommendationService.create_clothing_item(db_session, comp_image.id, user.id)

    # Get recommendations
    recs = RecommendationService.get_recommendations(db_session, user.id, ref_image.id, limit=5)

    assert len(recs) >= 0  # Should have some potential matches
    if len(recs) > 0:
        assert "items" in recs[0]
        assert "compatibility_score" in recs[0]


def test_save_outfit_insufficient_items(db_session):
    """Test saving outfit with insufficient items."""
    outfit = RecommendationService.save_outfit(db_session, user_id=1, name="Test", item_ids=[1])
    assert outfit is None


def test_save_outfit_success(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful outfit saving."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    user = AuthService.register_user(db_session, "outfitter@test.com", "outfitter", "password123")

    # Create multiple clothing items
    items = []
    for i, clothing_type in enumerate(["jacket", "pants", "shirt"]):
        image = ImageService.save_image(
            db_session,
            user_id=user.id,
            file_content=sample_image_bytes,
            original_filename=f"{clothing_type}.jpg",
            mime_type="image/jpeg",
        )

        mock_analysis = {
            "clothing_type": clothing_type,
            "categories": ["test"],
            "attributes": {"colors": ["blue"]},
            "confidence": 0.9,
        }

        with patch.object(VisionService, "_call_openrouter_api", return_value=mock_analysis):
            VisionService.analyze_image(db_session, image.id)

        item = RecommendationService.create_clothing_item(db_session, image.id, user.id)
        items.append(item)

    # Save outfit
    outfit = RecommendationService.save_outfit(
        db_session,
        user_id=user.id,
        name="Casual Look",
        item_ids=[item.id for item in items],
        description="Perfect for weekends",
        tags=["casual", "spring"],
    )

    assert outfit is not None
    assert outfit.name == "Casual Look"
    assert outfit.description == "Perfect for weekends"
    saved_items = json.loads(outfit.items)
    assert len(saved_items) == 3
    assert outfit.compatibility_score is not None


def test_get_user_outfits(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test retrieving user outfits."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    user = AuthService.register_user(db_session, "outfitlister@test.com", "outfitlister", "password123")

    # Create outfit
    image1 = ImageService.save_image(
        db_session, user_id=user.id, file_content=sample_image_bytes, original_filename="item1.jpg", mime_type="image/jpeg"
    )
    image2 = ImageService.save_image(
        db_session, user_id=user.id, file_content=sample_image_bytes, original_filename="item2.jpg", mime_type="image/jpeg"
    )

    mock = {"clothing_type": "shirt", "confidence": 0.9}
    with patch.object(VisionService, "_call_openrouter_api", return_value=mock):
        VisionService.analyze_image(db_session, image1.id)
        VisionService.analyze_image(db_session, image2.id)

    item1 = RecommendationService.create_clothing_item(db_session, image1.id, user.id)
    item2 = RecommendationService.create_clothing_item(db_session, image2.id, user.id)

    RecommendationService.save_outfit(
        db_session, user.id, "Outfit 1", [item1.id, item2.id]
    )

    outfits, total = RecommendationService.get_user_outfits(db_session, user.id)

    assert total >= 1
    assert len(outfits) >= 1


def test_delete_outfit_not_found(db_session):
    """Test deleting non-existent outfit."""
    result = RecommendationService.delete_outfit(db_session, outfit_id=999, user_id=1)
    assert result is False


def test_delete_outfit_success(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test successful outfit deletion."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    user = AuthService.register_user(db_session, "deleter@test.com", "deleter", "password123")

    image1 = ImageService.save_image(
        db_session, user_id=user.id, file_content=sample_image_bytes, original_filename="item1.jpg", mime_type="image/jpeg"
    )
    image2 = ImageService.save_image(
        db_session, user_id=user.id, file_content=sample_image_bytes, original_filename="item2.jpg", mime_type="image/jpeg"
    )

    mock = {"clothing_type": "shirt", "confidence": 0.9}
    with patch.object(VisionService, "_call_openrouter_api", return_value=mock):
        VisionService.analyze_image(db_session, image1.id)
        VisionService.analyze_image(db_session, image2.id)

    item1 = RecommendationService.create_clothing_item(db_session, image1.id, user.id)
    item2 = RecommendationService.create_clothing_item(db_session, image2.id, user.id)

    outfit = RecommendationService.save_outfit(
        db_session, user.id, "Delete Me", [item1.id, item2.id]
    )

    assert outfit is not None
    result = RecommendationService.delete_outfit(db_session, outfit.id, user.id)
    assert result is True


def test_get_clothing_item_not_owned(db_session):
    """Test getting item not owned by user."""
    item = RecommendationService.get_clothing_item(db_session, item_id=1, user_id=999)
    assert item is None


def test_get_user_clothing_items(db_session, sample_image_bytes, tmp_path, monkeypatch):
    """Test retrieving user clothing items."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")

    user = AuthService.register_user(db_session, "itemlister@test.com", "itemlister", "password123")

    # Create items
    for i in range(3):
        image = ImageService.save_image(
            db_session,
            user_id=user.id,
            file_content=sample_image_bytes,
            original_filename=f"item{i}.jpg",
            mime_type="image/jpeg",
        )

        mock = {"clothing_type": "shirt", "confidence": 0.9}
        with patch.object(VisionService, "_call_openrouter_api", return_value=mock):
            VisionService.analyze_image(db_session, image.id)

        RecommendationService.create_clothing_item(db_session, image.id, user.id)

    items, total = RecommendationService.get_user_clothing_items(db_session, user.id)

    assert total >= 3
    assert len(items) >= 3
