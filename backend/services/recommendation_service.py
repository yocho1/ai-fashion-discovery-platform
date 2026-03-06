from datetime import datetime
import json
import logging
from types import SimpleNamespace
from typing import Optional, List, Tuple, Dict, Any

# import numpy as np  # TEMPORARILY DISABLED - numpy import issue
from sqlalchemy.orm import Session

from db.models import ClothingItem, VisionAnalysis, Outfit, Image
from services.embedding_service import EmbeddingService
from services.vision_service import VisionService
from services.cache_service import CacheService

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating outfit recommendations based on clothing embeddings."""

    OUTFIT_MIN_ITEMS = 2
    OUTFIT_MAX_ITEMS = 5
    MIN_COMPATIBILITY = 0.5

    @staticmethod
    def create_clothing_item(
        db: Session, image_id: int, user_id: int, visibility: str = "private"
    ) -> Optional[ClothingItem]:
        """
        Create a clothing item from analyzed image.
        
        Args:
            db: Database session
            image_id: ID of the analyzed image
            user_id: User ID (owner)
            visibility: "private" or "public"
            
        Returns:
            ClothingItem or None if image not found/analyzed
        """
        # Get image
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            logger.warning(f"Image {image_id} not found")
            return None

        # Get vision analysis
        analysis = VisionService.get_analysis(db, image_id)
        if not analysis or analysis.analysis_status != "completed":
            logger.warning(f"No completed analysis for image {image_id}")
            return None

        # Parse attributes
        attributes = {}
        if analysis.attributes:
            try:
                attributes = json.loads(analysis.attributes)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse attributes for image {image_id}")

        # Generate embedding
        embedding_array = EmbeddingService.generate_embedding(attributes)
        embedding_bytes = None
        if embedding_array is not None:
            embedding_bytes = EmbeddingService.serialize_embedding(embedding_array)

        # Parse categories
        categories = []
        if analysis.categories:
            try:
                categories = json.loads(analysis.categories)
            except json.JSONDecodeError:
                pass

        # Create clothing item
        item = ClothingItem(
            image_id=image_id,
            user_id=user_id,
            clothing_type=analysis.clothing_type or "unknown",
            categories=json.dumps(categories),
            attributes=analysis.attributes,
            embedding=embedding_bytes,
            visibility=visibility,
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        # Invalidate cache for user's clothing items and recommendations
        CacheService.invalidate_user_clothing_items(user_id)

        logger.info(f"Created clothing item {item.id} from image {image_id}")
        return item

    @staticmethod
    def get_recommendations(
        db: Session,
        user_id: int,
        reference_image_id: int,
        limit: int = 5,
        min_complementary_items: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Get outfit recommendations based on a reference image.
        
        Args:
            db: Database session
            user_id: User ID
            reference_image_id: Base image for recommendations
            limit: Number of recommendations to return
            min_complementary_items: Minimum items in outfit
            
        Returns:
            List of outfit recommendation dictionaries
        """
        # Check cache first
        cached_recommendations = CacheService.get_recommendations(user_id, reference_image_id)
        if cached_recommendations is not None:
            logger.debug(f"Returning cached recommendations for user {user_id}, image {reference_image_id}")
            return cached_recommendations[:limit]

        # Get clothing item for reference image
        ref_item = db.query(ClothingItem).filter(
            ClothingItem.image_id == reference_image_id, ClothingItem.user_id == user_id
        ).first()

        if not ref_item:
            logger.warning(f"Clothing item for image {reference_image_id} not found")
            return []

        if not ref_item.embedding:
            logger.warning(f"No embedding for item {ref_item.id}")
            return []

        # Deserialize reference embedding
        ref_embedding = EmbeddingService.deserialize_embedding(ref_item.embedding)
        if ref_embedding is None:
            return []

        # Get complementary items
        all_items = db.query(ClothingItem).filter(ClothingItem.user_id == user_id).all()

        outfits = []

        # Generate outfit combinations
        for item in all_items:
            if item.id == ref_item.id:
                continue  # Skip self

            if not item.embedding:
                continue

            comp_embedding = EmbeddingService.deserialize_embedding(item.embedding)
            if comp_embedding is None:
                continue

            # Calculate outfit compatibility
            compatibility = EmbeddingService.calculate_outfit_compatibility(
                [ref_embedding, comp_embedding]
            )

            same_type = (item.clothing_type or "other") == ref_item.clothing_type

            if compatibility >= RecommendationService.MIN_COMPATIBILITY:
                if same_type:
                    suggestion = f"Style alternative: swap your {ref_item.clothing_type} with this {item.clothing_type}"
                else:
                    suggestion = f"Pair {ref_item.clothing_type} with {item.clothing_type}"

                outfit_dict = {
                    "items": [
                        {
                            "id": ref_item.id,
                            "image_id": ref_item.image_id,
                            "clothing_type": ref_item.clothing_type,
                        },
                        {
                            "id": item.id,
                            "image_id": item.image_id,
                            "clothing_type": item.clothing_type,
                        },
                    ],
                    "compatibility_score": compatibility,
                    "suggestion": suggestion,
                }
                outfits.append(outfit_dict)

        # Sort by compatibility descending
        outfits.sort(key=lambda x: x["compatibility_score"], reverse=True)
        
        # Cache results
        CacheService.set_recommendations(user_id, reference_image_id, outfits)
        
        return outfits[:limit]

    @staticmethod
    def save_outfit(
        db: Session,
        user_id: int,
        name: str,
        item_ids: List[int],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Outfit]:
        """
        Save an outfit combination.
        
        Args:
            db: Database session
            user_id: User ID (owner)
            name: Outfit name
            item_ids: List of clothing item IDs in outfit
            description: Optional description
            tags: Optional list of tags (occasion, season, etc.)
            
        Returns:
            Created Outfit or None if failed
        """
        if len(item_ids) < RecommendationService.OUTFIT_MIN_ITEMS:
            logger.warning(f"Outfit has too few items ({len(item_ids)})")
            return None

        # Verify all items belong to user
        items = db.query(ClothingItem).filter(
            ClothingItem.id.in_(item_ids), ClothingItem.user_id == user_id
        ).all()

        if len(items) != len(item_ids):
            logger.warning(f"Not all items belong to user {user_id}")
            return None

        # Calculate compatibility score
        embeddings = []
        for item in items:
            if item.embedding:
                emb = EmbeddingService.deserialize_embedding(item.embedding)
                if emb is not None:
                    embeddings.append(emb)

        compatibility_score = 0.5
        if len(embeddings) > 1:
            compatibility_score = EmbeddingService.calculate_outfit_compatibility(embeddings)

        # Create outfit
        outfit = Outfit(
            user_id=user_id,
            name=name,
            description=description,
            items=json.dumps(item_ids),
            compatibility_score=compatibility_score,
            tags=json.dumps(tags or []),
        )

        db.add(outfit)
        db.commit()
        db.refresh(outfit)

        # Invalidate outfit cache
        CacheService.invalidate_user_outfits(user_id)

        logger.info(f"Created outfit {outfit.id} for user {user_id}")
        return outfit

    @staticmethod
    def get_user_outfits(
        db: Session, user_id: int, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Outfit], int]:
        """Get all outfits for a user."""
        # Check cache first
        cached_data = CacheService.get_outfits(user_id, limit, offset)
        if cached_data is not None:
            logger.debug(f"Returning cached outfits for user {user_id}")
            cached_outfits = []
            for cached_outfit in cached_data.get("outfits", []):
                outfit_data = dict(cached_outfit)
                created_at_value = outfit_data.get("created_at")
                if isinstance(created_at_value, str):
                    try:
                        outfit_data["created_at"] = datetime.fromisoformat(created_at_value)
                    except ValueError:
                        pass
                cached_outfits.append(SimpleNamespace(**outfit_data))
            return cached_outfits, cached_data.get("total", len(cached_outfits))
        
        query = db.query(Outfit).filter(Outfit.user_id == user_id)
        total = query.count()
        outfits = query.order_by(Outfit.created_at.desc()).limit(limit).offset(offset).all()
        
        # Cache results
        cache_data = {
            "outfits": [
                {
                    "id": outfit.id,
                    "user_id": outfit.user_id,
                    "name": outfit.name,
                    "description": outfit.description,
                    "items": outfit.items,
                    "compatibility_score": outfit.compatibility_score,
                    "tags": outfit.tags,
                    "created_at": outfit.created_at.isoformat(),
                }
                for outfit in outfits
            ],
            "total": total,
        }
        CacheService.set_outfits(user_id, limit, offset, cache_data)
        
        return outfits, total

    @staticmethod
    def delete_outfit(db: Session, outfit_id: int, user_id: int) -> bool:
        """Delete an outfit (verify ownership)."""
        outfit = db.query(Outfit).filter(Outfit.id == outfit_id, Outfit.user_id == user_id).first()

        if not outfit:
            logger.warning(f"Outfit {outfit_id} not found or not owned by user {user_id}")
            return False

        db.delete(outfit)
        db.commit()
        
        # Invalidate outfit cache
        CacheService.invalidate_user_outfits(user_id)
        
        logger.info(f"Deleted outfit {outfit_id}")
        return True

    @staticmethod
    def get_clothing_item(
        db: Session, item_id: int, user_id: int
    ) -> Optional[ClothingItem]:
        """Get a clothing item (verify ownership)."""
        return db.query(ClothingItem).filter(
            ClothingItem.id == item_id, ClothingItem.user_id == user_id
        ).first()

    @staticmethod
    def get_user_clothing_items(
        db: Session, user_id: int, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ClothingItem], int]:
        """Get all clothing items for a user."""
        # Check cache first
        cached_data = CacheService.get_clothing_items(user_id, limit, offset)
        if cached_data is not None:
            logger.debug(f"Returning cached clothing items for user {user_id}")
            cached_items = []
            for cached_item in cached_data.get("items", []):
                item_data = dict(cached_item)
                created_at_value = item_data.get("created_at")
                if isinstance(created_at_value, str):
                    try:
                        item_data["created_at"] = datetime.fromisoformat(created_at_value)
                    except ValueError:
                        pass
                cached_items.append(SimpleNamespace(**item_data))
            return cached_items, cached_data.get("total", len(cached_items))
        
        query = db.query(ClothingItem).filter(ClothingItem.user_id == user_id)
        total = query.count()
        items = query.order_by(ClothingItem.created_at.desc()).limit(limit).offset(offset).all()
        
        # Cache results
        cache_data = {
            "items": [
                {
                    "id": item.id,
                    "image_id": item.image_id,
                    "user_id": item.user_id,
                    "clothing_type": item.clothing_type,
                    "categories": item.categories,
                    "attributes": item.attributes,
                    "visibility": item.visibility,
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ],
            "total": total,
        }
        CacheService.set_clothing_items(user_id, limit, offset, cache_data)
        
        return items, total
