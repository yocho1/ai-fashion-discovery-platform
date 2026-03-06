import tempfile
from pathlib import Path

import pytest

from services.storage_service import StorageService


def test_generate_filename():
    """Test filename generation."""
    filename = StorageService.generate_filename("test.jpg", user_id=123)

    assert filename.endswith(".jpg")
    assert "123" in filename


def test_save_file(tmp_path, monkeypatch):
    """Test file saving."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    file_content = b"test image data"
    filename, file_path = StorageService.save_file(file_content, user_id=1, original_filename="test.jpg")

    assert Path(file_path).exists()

    # Verify file content
    with open(file_path, "rb") as f:
        assert f.read() == file_content


def test_delete_file(tmp_path, monkeypatch):
    """Test file deletion."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    file_content = b"test"
    filename, file_path = StorageService.save_file(file_content, user_id=1, original_filename="test.jpg")

    assert Path(file_path).exists()

    result = StorageService.delete_file(file_path)

    assert result is True
    assert not Path(file_path).exists()


def test_get_file(tmp_path, monkeypatch):
    """Test file retrieval."""
    from core.config import settings

    monkeypatch.setattr(settings, "local_storage_path", str(tmp_path))

    file_content = b"test image"
    filename, file_path = StorageService.save_file(file_content, user_id=1, original_filename="test.jpg")

    retrieved = StorageService.get_file(file_path)

    assert retrieved == file_content
