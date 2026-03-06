import hashlib
import os
from pathlib import Path
from typing import BinaryIO, Optional

from core.config import settings


class StorageService:
    """Handle file storage operations (local or S3)."""

    @staticmethod
    def get_storage_path() -> Path:
        """Get or create storage directory."""
        storage_path = Path(settings.local_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    @staticmethod
    def generate_filename(original_filename: str, user_id: int) -> str:
        """Generate a unique filename."""
        ext = Path(original_filename).suffix
        timestamp = int(os.urandom(4).hex(), 16)
        unique_name = f"{user_id}_{timestamp}{ext}"
        return unique_name

    @staticmethod
    def save_file(file_content: bytes, user_id: int, original_filename: str) -> tuple[str, str]:
        """
        Save file to storage.
        Returns: (filename, file_path)
        """
        filename = StorageService.generate_filename(original_filename, user_id)
        file_path = StorageService.get_storage_path() / filename

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_content)

        return filename, str(file_path)

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file from storage."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def get_file(file_path: str) -> Optional[bytes]:
        """Retrieve file content."""
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception:
            return None
