import json
import numpy as np
import pickle

import pytest

from services.embedding_service import EmbeddingService
from db.models import ClothingItem


def test_generate_embedding_basic():
    """Test basic embedding generation."""
    attributes = {
        "colors": ["navy", "white"],
        "patterns": ["solid"],
        "materials": ["cotton"],
        "style": ["casual", "sporty"],
        "fit": "regular",
    }

    embedding = EmbeddingService.generate_embedding(attributes)

    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == EmbeddingService.EMBEDDING_DIMENSION
    assert np.all(np.isfinite(embedding))  # No NaN or inf


def test_generate_embedding_empty():
    """Test embedding generation with empty attributes."""
    embedding = EmbeddingService.generate_embedding({})
    assert embedding is None


def test_generate_embedding_partial():
    """Test embedding generation with partial attributes."""
    attributes = {"colors": ["blue"]}

    embedding = EmbeddingService.generate_embedding(attributes)

    assert embedding is not None
    assert len(embedding) == EmbeddingService.EMBEDDING_DIMENSION


def test_serialize_deserialize_embedding():
    """Test embedding serialization/deserialization."""
    original = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)

    serialized = EmbeddingService.serialize_embedding(original)
    assert isinstance(serialized, bytes)

    deserialized = EmbeddingService.deserialize_embedding(serialized)
    assert deserialized is not None
    assert np.allclose(original, deserialized)


def test_deserialize_invalid_bytes():
    """Test deserialization of invalid bytes."""
    result = EmbeddingService.deserialize_embedding(b"invalid")
    assert result is None


def test_find_similar_items_empty(db_session):
    """Test finding similar items with no items in database."""
    query_embedding = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)

    results = EmbeddingService.find_similar_items(db_session, query_embedding, user_id=999)

    assert len(results) == 0


def test_find_similar_items_with_results(db_session):
    """Test finding similar items."""
    from services.auth_service import AuthService
    from db.models import Image

    user = AuthService.register_user(db_session, "embedder@test.com", "embedder", "password123")

    # Create clothing items
    query_embedding = np.ones(EmbeddingService.EMBEDDING_DIMENSION) * 0.5
    query_embedding = query_embedding / np.linalg.norm(query_embedding)

    # Create highly similar embedding
    similar_embedding = query_embedding + np.random.randn(EmbeddingService.EMBEDDING_DIMENSION) * 0.01
    similar_embedding = similar_embedding / np.linalg.norm(similar_embedding)

    # Create very different embedding
    different_embedding = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)
    different_embedding = different_embedding / np.linalg.norm(different_embedding)

    items = []
    for i, emb in enumerate([similar_embedding, different_embedding]):
        image = Image(
            user_id=user.id,
            filename=f"item_{i}.jpg",
            original_filename=f"item_{i}.jpg",
            file_path=f"./uploads/item_{i}.jpg",
            file_size=50000,
            mime_type="image/jpeg",
            width=500,
            height=500,
        )
        db_session.add(image)
        db_session.commit()

        item = ClothingItem(
            image_id=image.id,
            user_id=user.id,
            clothing_type="shirt",
            embedding=EmbeddingService.serialize_embedding(emb),
        )
        db_session.add(item)
        db_session.commit()
        items.append(item)

    results = EmbeddingService.find_similar_items(
        db_session, query_embedding, user_id=user.id, limit=10, min_similarity=0.7
    )

    # Should find at least the similar item
    assert len(results) >= 1
    assert results[0][0].id == items[0].id  # Most similar should be first


def test_find_similar_items_with_filter(db_session):
    """Test finding similar items with clothing type filter."""
    from services.auth_service import AuthService
    from db.models import Image

    user = AuthService.register_user(db_session, "filterer@test.com", "filterer", "password123")

    query_embedding = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)
    query_embedding = query_embedding / np.linalg.norm(query_embedding)

    # Create item with different type
    image = Image(
        user_id=user.id,
        filename="pants.jpg",
        original_filename="pants.jpg",
        file_path="./uploads/pants.jpg",
        file_size=50000,
        mime_type="image/jpeg",
        width=500,
        height=500,
    )
    db_session.add(image)
    db_session.commit()

    item = ClothingItem(
        image_id=image.id,
        user_id=user.id,
        clothing_type="pants",
        embedding=EmbeddingService.serialize_embedding(query_embedding),
    )
    db_session.add(item)
    db_session.commit()

    # Filter by different clothing type
    results = EmbeddingService.find_similar_items(
        db_session, query_embedding, user_id=user.id, clothing_type_filter="shirt"
    )

    assert len(results) == 0

    # Filter by correct clothing type
    results = EmbeddingService.find_similar_items(
        db_session, query_embedding, user_id=user.id, clothing_type_filter="pants"
    )

    assert len(results) == 1


def test_calculate_outfit_compatibility_single_item():
    """Test outfit compatibility with single item."""
    embeddings = [np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)]
    score = EmbeddingService.calculate_outfit_compatibility(embeddings)
    assert score == 1.0


def test_calculate_outfit_compatibility_two_items():
    """Test outfit compatibility with two items."""
    emb1 = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)
    emb2 = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)

    embeddings = [emb1, emb2]
    score = EmbeddingService.calculate_outfit_compatibility(embeddings)

    assert isinstance(score, float)
    assert 0 <= score <= 1


def test_calculate_outfit_compatibility_similar_items():
    """Test outfit compatibility with similar items."""
    emb1 = np.random.randn(EmbeddingService.EMBEDDING_DIMENSION)
    emb1 = emb1 / np.linalg.norm(emb1)

    # Create similar embedding
    emb2 = emb1 + np.random.randn(EmbeddingService.EMBEDDING_DIMENSION) * 0.01
    emb2 = emb2 / np.linalg.norm(emb2)

    embeddings = [emb1, emb2]
    score = EmbeddingService.calculate_outfit_compatibility(embeddings)

    # Similar items should have high compatibility
    assert score > 0.5
