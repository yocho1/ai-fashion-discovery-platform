import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.images import router as images_router
from api.routes.vision import router as vision_router
from api.routes.recommendations import router as recommendations_router
from core.config import settings
from db.session import init_db

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.1.0")

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize database tables (non-blocking)
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database initialization failed (will retry on next startup): {e}")

    application.include_router(health_router, prefix="/health", tags=["health"])
    application.include_router(auth_router, prefix="/auth", tags=["auth"])
    application.include_router(images_router, prefix="/images", tags=["images"])
    application.include_router(vision_router, prefix="/vision", tags=["vision"])
    application.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
    return application


app = create_app()
