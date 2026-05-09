"""
Pytest configuration and fixtures.
"""

import sys
from pathlib import Path

import pytest
from PIL import Image

# Add src to pythonpath for tests if not already there
# This allows running pytest tests/ from the desktop-app directory
src_dir = str(Path(__file__).parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


@pytest.fixture
def temp_image_file(tmp_path):
    """Create a temporary test image file."""
    img_path = tmp_path / "test_image.jpg"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(img_path, quality=95)
    return img_path


@pytest.fixture
def temp_image_files(tmp_path):
    """Create multiple temporary test image files."""
    files = []
    for i in range(3):
        img_path = tmp_path / f"test_image_{i}.jpg"
        img = Image.new("RGB", (100, 100), color=["red", "green", "blue"][i])
        img.save(img_path, quality=95)
        files.append(img_path)
    return files


@pytest.fixture
def temp_pdf_file(tmp_path, temp_image_files):
    """Create a temporary PDF file for testing."""
    from src.core.converters import ConversionEngine

    pdf_path = tmp_path / "test.pdf"
    engine = ConversionEngine()
    success = engine.images_to_pdf(temp_image_files, pdf_path, "A4")
    assert success, "Failed to create test PDF"
    return pdf_path
