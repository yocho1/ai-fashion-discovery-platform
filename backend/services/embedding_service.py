import json
import logging
import pickle
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session

from db.models import ClothingItem, Image

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing clothing embeddings for similarity search."""

    EMBEDDING_DIMENSION = 128

    @staticmethod
    def generate_embedding(clothing_attributes: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Generate a numerical embedding from clothing attributes.
        
        Args:
            clothing_attributes: Dictionary with colors, patterns, materials, style, etc.
            
        Returns:
            Numpy array of shape (EMBEDDING_DIMENSION,) or None if failed
        """
        try:
            # Extract text features from attributes
            feature_text = EmbeddingService._attributes_to_text(clothing_attributes)

            if not feature_text:
                logger.warning("Empty feature text for embedding generation")
                return None

            # Use TfidfVectorizer to create embedding (produces sparse to dense conversion)
            vectorizer = TfidfVectorizer(
                max_features=EmbeddingService.EMBEDDING_DIMENSION,
                lowercase=True,
                stop_words="english",
            )

            # Fit and transform feature text
            # Note: For production, this should use a pre-trained model
            embedding = vectorizer.fit_transform([feature_text]).toarray()[0]

            # Pad or truncate to EMBEDDING_DIMENSION
            if len(embedding) < EmbeddingService.EMBEDDING_DIMENSION:
                embedding = np.pad(
                    embedding,
                    (0, EmbeddingService.EMBEDDING_DIMENSION - len(embedding)),
                    mode="constant",
                )
            else:
                embedding = embedding[: EmbeddingService.EMBEDDING_DIMENSION]

            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None

    @staticmethod
    def _attributes_to_text(attributes: Dict[str, Any]) -> str:
        """Convert attributes dictionary to searchable text."""
        parts = []

        if attributes.get("colors"):
            parts.append(" ".join(attributes["colors"]))

        if attributes.get("patterns"):
            parts.append(" ".join(attributes["patterns"]))

        if attributes.get("materials"):
            parts.append(" ".join(attributes["materials"]))

        if attributes.get("style"):
            style = attributes["style"]
            if isinstance(style, list):
                parts.append(" ".join(style))
            else:
                parts.append(str(style))

        if attributes.get("fit"):
            parts.append(attributes["fit"])

        if attributes.get("season"):
            seasons = attributes["season"]
            if isinstance(seasons, list):
                parts.append(" ".join(seasons))
            else:
                parts.append(str(seasons))

        return " ".join(parts)

    @staticmethod
    def serialize_embedding(embedding: np.ndarray) -> bytes:
        """Convert numpy array to bytes for storage."""
        return pickle.dumps(embedding)

    @staticmethod
    def deserialize_embedding(embedding_bytes: bytes) -> Optional[np.ndarray]:
        """Convert bytes back to numpy array."""
        try:
            return pickle.loads(embedding_bytes)
        except Exception as e:
            logger.error(f"Error deserializing embedding: {str(e)}")
            return None

    @staticmethod
    def find_similar_items(
        db: Session,
        query_embedding: np.ndarray,
        user_id: int,
        limit: int = 10,
        clothing_type_filter: Optional[str] = None,
        min_similarity: float = 0.3,
    ) -> List[Tuple[ClothingItem, float]]:
        """
        Find similar clothing items based on embedding distance.
        
        Args:
            db: Database session
            query_embedding: Query embedding vector
            user_id: User ID to filter by
            limit: Maximum number of results
            clothing_type_filter: Optional clothing type to filter by
            min_similarity: Minimum similarity score (0-1)
            
        Returns:
            List of (ClothingItem, similarity_score) tuples
        """
        from sklearn.metrics.pairwise import cosine_similarity

        query = db.query(ClothingItem).filter(ClothingItem.user_id == user_id)

        if clothing_type_filter:
            query = query.filter(ClothingItem.clothing_type == clothing_type_filter)

        items = query.all()
        results = []

        for item in items:
            if not item.embedding:
                continue

            try:
                item_embedding = EmbeddingService.deserialize_embedding(item.embedding)
                if item_embedding is None:
                    continue

                # Reshape for cosine_similarity
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1), item_embedding.reshape(1, -1)
                )[0][0]

                if similarity >= min_similarity:
                    results.append((item, float(similarity)))

            except Exception as e:
                logger.warning(f"Error computing similarity for item {item.id}: {str(e)}")
                continue

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    @staticmethod
    def calculate_outfit_compatibility(
        item_embeddings: List[np.ndarray],
    ) -> float:
        """
        Calculate how well clothing items work together.
        
        Args:
            item_embeddings: List of clothing item embeddings
            
        Returns:
            Compatibility score (0-1, where 1 is perfect match)
        """
        from sklearn.metrics.pairwise import cosine_similarity

        if len(item_embeddings) < 2:
            return 1.0

        try:
            # Calculate pairwise similarities
            similarities = []
            for i in range(len(item_embeddings)):
                for j in range(i + 1, len(item_embeddings)):
                    sim = cosine_similarity(
                        item_embeddings[i].reshape(1, -1),
                        item_embeddings[j].reshape(1, -1),
                    )[0][0]
                    similarities.append(sim)

            if not similarities:
                return 0.5

            # Average similarity as compatibility
            compatibility = np.mean(similarities)
            # Normalize to 0-1 range better (encourage diversity)
            # High similarity (>0.8) is good, but we also want some variety
            # So we map [0, 1] to a different scale
            return float(np.clip(compatibility * 0.9 + 0.1, 0, 1))

        except Exception as e:
            logger.error(f"Error calculating outfit compatibility: {str(e)}")
            return 0.5
