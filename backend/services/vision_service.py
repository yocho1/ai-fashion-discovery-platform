import base64
from datetime import datetime
import json
import logging
from types import SimpleNamespace
from typing import Optional, Dict, Any

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from db.models import VisionAnalysis, Image
from services.storage_service import StorageService
from services.cache_service import CacheService

logger = logging.getLogger(__name__)


class VisionService:
    """Service for analyzing clothing attributes using OpenRouter AI Vision API."""

    CLOTHING_ANALYSIS_PROMPT = """Analyze this fashion image and provide detailed clothing information.

Return a JSON object with the following structure:
{
    "clothing_type": "main clothing item (e.g., jacket, shirt, pants, dress)",
    "categories": ["list", "of", "clothing", "categories"],
    "attributes": {
        "colors": ["list", "of", "colors"],
        "patterns": ["list", "of", "patterns (solid, striped, floral, etc.)"],
        "materials": ["list", "of", "materials (cotton, wool, leather, etc.)"],
        "style": ["list", "of", "style descriptors (casual, formal, sporty, etc.)"],
        "fit": "fit type (slim, regular, oversized, etc.)",
        "season": ["list", "of", "suitable seasons"]
    },
    "confidence": 0.95,
    "description": "Brief description of the clothing item"
}

Be precise and specific. If you're unsure about a field, omit it or set to null."""

    @staticmethod
    def analyze_image(db: Session, image_id: int) -> Optional[VisionAnalysis]:
        """
        Analyze an image using OpenRouter vision API.
        
        Args:
            db: Database session
            image_id: ID of the image to analyze
            
        Returns:
            VisionAnalysis object with results or None if image not found
            
        Raises:
            ValueError: If OpenRouter API key is not configured
        """
        # Get image from database
        image = db.query(Image).filter(Image.id == image_id).first()
        if not image:
            logger.warning(f"Image {image_id} not found")
            return None

        # Check if analysis already exists and is completed
        existing = db.query(VisionAnalysis).filter(VisionAnalysis.image_id == image_id).first()
        if existing and existing.analysis_status == "completed":
            return existing

        # Validate API key
        if not settings.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Use existing record or create new one
        if existing:
            analysis = existing
        else:
            analysis = VisionAnalysis(
                image_id=image_id,
                analysis_status="pending",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)

        try:
            # Read image file and convert to base64
            image_data = StorageService.get_file(image.file_path)
            base64_image = base64.b64encode(image_data).decode("utf-8")

            # Determine media type
            media_type = image.mime_type or "image/jpeg"

            # Call OpenRouter API
            result = VisionService._call_openrouter_api(
                base64_image, media_type
            )

            # Parse and store results
            if result:
                analysis.clothing_type = result.get("clothing_type", "unknown")
                analysis.categories = json.dumps(result.get("categories", []))
                analysis.attributes = json.dumps(result.get("attributes", {}))
                analysis.overall_confidence = float(result.get("confidence", 0.0))
                analysis.analysis_status = "completed"
                analysis.error_message = None
            else:
                analysis.analysis_status = "failed"
                analysis.error_message = "Failed to parse API response"

        except Exception as e:
            logger.error(f"Vision analysis error for image {image_id}: {str(e)}")
            analysis.analysis_status = "failed"
            analysis.error_message = str(e)[:500]

        db.commit()
        db.refresh(analysis)

        # Update caches after analysis completion/update
        if analysis.analysis_status == "completed":
            CacheService.set_vision_analysis(
                image_id,
                {
                    "id": analysis.id,
                    "image_id": analysis.image_id,
                    "clothing_type": analysis.clothing_type,
                    "categories": analysis.categories,
                    "attributes": analysis.attributes,
                    "overall_confidence": analysis.overall_confidence,
                    "analysis_status": analysis.analysis_status,
                    "error_message": analysis.error_message,
                    "model_used": analysis.model_used,
                    "created_at": analysis.created_at.isoformat(),
                    "updated_at": analysis.updated_at.isoformat(),
                },
            )
        CacheService.invalidate_user_analyses(image.user_id)

        return analysis

    @staticmethod
    def _call_openrouter_api(base64_image: str, media_type: str) -> Optional[Dict[str, Any]]:
        """
        Call OpenRouter API with image for clothing analysis.
        
        Args:
            base64_image: Base64 encoded image data
            media_type: MIME type of the image (e.g., "image/jpeg")
            
        Returns:
            Parsed JSON response from API or None if failed
        """
        try:
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aifashion-discovery.com",
                "X-Title": "AI Fashion Discovery",
            }

            payload = {
                "model": settings.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}",
                                },
                            },
                            {
                                "type": "text",
                                "text": VisionService.CLOTHING_ANALYSIS_PROMPT,
                            },
                        ],
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
            }

            with httpx.Client(timeout=settings.vision_api_timeout) as client:
                response = client.post(
                    f"{settings.openrouter_api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None

            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse JSON from response
            # Response might be wrapped in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response as JSON: {str(e)}")
            return None
        except httpx.RequestError as e:
            logger.error(f"OpenRouter API request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in OpenRouter API call: {str(e)}")
            return None

    @staticmethod
    def get_analysis(db: Session, image_id: int) -> Optional[VisionAnalysis]:
        """Get vision analysis for an image."""
        # Check cache first (vision analysis is immutable, so long TTL is ok)
        cached_analysis = CacheService.get_vision_analysis(image_id)
        if cached_analysis is not None:
            logger.debug(f"Returning cached vision analysis for image {image_id}")
            analysis_data = dict(cached_analysis)
            for date_field in ("created_at", "updated_at"):
                date_value = analysis_data.get(date_field)
                if isinstance(date_value, str):
                    try:
                        analysis_data[date_field] = datetime.fromisoformat(date_value)
                    except ValueError:
                        pass
            return SimpleNamespace(**analysis_data)
        
        analysis = db.query(VisionAnalysis).filter(VisionAnalysis.image_id == image_id).first()
        
        # Cache the analysis if found
        if analysis:
            cache_data = {
                "id": analysis.id,
                "image_id": analysis.image_id,
                "clothing_type": analysis.clothing_type,
                "categories": analysis.categories,
                "attributes": analysis.attributes,
                "overall_confidence": analysis.overall_confidence,
                "analysis_status": analysis.analysis_status,
                "error_message": analysis.error_message,
                "model_used": analysis.model_used,
                "created_at": analysis.created_at.isoformat(),
                "updated_at": analysis.updated_at.isoformat(),
            }
            CacheService.set_vision_analysis(image_id, cache_data)
        
        return analysis

    @staticmethod
    def get_user_analyses(
        db: Session, user_id: int, limit: int = 50, offset: int = 0
    ) -> tuple[list[VisionAnalysis], int]:
        """Get all vision analyses for a user's images."""
        # Check cache first
        cached_data = CacheService.get_user_analyses(user_id, limit, offset)
        if cached_data is not None:
            logger.debug(f"Returning cached user analyses for user {user_id}")
            cached_analyses = []
            for cached_analysis in cached_data.get("analyses", []):
                analysis_data = dict(cached_analysis)
                for date_field in ("created_at", "updated_at"):
                    date_value = analysis_data.get(date_field)
                    if isinstance(date_value, str):
                        try:
                            analysis_data[date_field] = datetime.fromisoformat(date_value)
                        except ValueError:
                            pass
                cached_analyses.append(SimpleNamespace(**analysis_data))
            return cached_analyses, cached_data.get("total", len(cached_analyses))
        
        query = db.query(VisionAnalysis).join(Image).filter(Image.user_id == user_id)
        total = query.count()
        analyses = query.order_by(VisionAnalysis.created_at.desc()).limit(limit).offset(offset).all()
        
        # Cache results
        cache_data = {
            "analyses": [
                {
                    "id": analysis.id,
                    "image_id": analysis.image_id,
                    "clothing_type": analysis.clothing_type,
                    "categories": analysis.categories,
                    "attributes": analysis.attributes,
                    "overall_confidence": analysis.overall_confidence,
                    "analysis_status": analysis.analysis_status,
                    "error_message": analysis.error_message,
                    "model_used": analysis.model_used,
                    "created_at": analysis.created_at.isoformat(),
                    "updated_at": analysis.updated_at.isoformat(),
                }
                for analysis in analyses
            ],
            "total": total,
        }
        CacheService.set_user_analyses(user_id, limit, offset, cache_data)
        
        return analyses, total
