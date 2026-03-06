from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Fashion Discovery API"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://fashion:fashion@localhost:5432/fashion_db"
    redis_url: str = "redis://localhost:6379/0"

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # JWT settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Storage settings
    storage_type: str = "local"  # local or s3
    local_storage_path: str = "./uploads"
    max_upload_size_mb: int = 10
    allowed_image_types: list = ["image/jpeg", "image/png", "image/webp"]
    min_image_dimension: int = 200

    # AWS S3 settings (optional)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_s3_region: Optional[str] = "us-east-1"

    # OpenRouter API settings (for vision analysis)
    openrouter_api_key: Optional[str] = None
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    vision_model: str = "openai/gpt-4o-mini"  # Model for clothing detection
    vision_api_timeout: int = 60  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
