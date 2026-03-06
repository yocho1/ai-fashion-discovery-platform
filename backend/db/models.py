from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Text, Float, LargeBinary
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String(50), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    description = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Image(id={self.id}, user_id={self.user_id}, filename={self.filename})>"


class VisionAnalysis(Base):
    __tablename__ = "vision_analyses"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), index=True, nullable=False, unique=True)
    clothing_type = Column(String(100), nullable=True)  # e.g., "jacket", "shirt", "pants"
    categories = Column(Text, nullable=True)  # JSON string of categories
    attributes = Column(Text, nullable=True)  # JSON string of attributes (color, pattern, material, etc.)
    overall_confidence = Column(Float, nullable=True)  # 0.0-1.0
    analysis_status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    error_message = Column(String(500), nullable=True)  # Error details if analysis failed
    model_used = Column(String(100), default="openrouter-vision", nullable=False)  # Track which model processed it
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<VisionAnalysis(id={self.id}, image_id={self.image_id}, status={self.analysis_status})>"


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), index=True, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    clothing_type = Column(String(100), nullable=False)
    categories = Column(Text, nullable=True)  # JSON array of category tags
    attributes = Column(Text, nullable=True)  # JSON object of detailed attributes
    embedding = Column(LargeBinary, nullable=True)  # Binary serialized numpy array
    embedding_model = Column(String(50), default="default", nullable=False)
    visibility = Column(String(20), default="private", nullable=False)  # private or public
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ClothingItem(id={self.id}, user_id={self.user_id}, type={self.clothing_type})>"


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    items = Column(Text, nullable=False)  # JSON array of clothing item IDs
    compatibility_score = Column(Float, nullable=True)  # Overall outfit score
    tags = Column(Text, nullable=True)  # JSON array of tags (occasion, season, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Outfit(id={self.id}, user_id={self.user_id}, name={self.name})>"
