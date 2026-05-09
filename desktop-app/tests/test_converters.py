"""
Tests for conversion engine.
"""

from pathlib import Path

import fitz  # PyMuPDF
import pytest
from PIL import Image, ImageStat

from src.core.converters import ConversionEngine
from src.core.privacy import ensure_rgb_mode, strip_image_metadata


class TestConversionEngine:
    """Test conversion engine functionality."""

    def test_images_to_pdf_single_image(self, temp_image_file, tmp_path):
        """Test converting a single image to PDF."""
        engine = ConversionEngine()
        output_pdf = tmp_path / "output.pdf"

        result = engine.images_to_pdf([temp_image_file], output_pdf, "A4")

        assert result is True
        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 0

    def test_images_to_pdf_multiple_images(self, temp_image_files, tmp_path):
        """Test converting multiple images to PDF."""
        engine = ConversionEngine()
        output_pdf = tmp_path / "output.pdf"

        result = engine.images_to_pdf(temp_image_files, output_pdf, "A4")

        assert result is True
        assert output_pdf.exists()

        # Verify PDF has correct number of pages
        doc = fitz.open(str(output_pdf))
        assert len(doc) == len(temp_image_files)
        doc.close()

    def test_images_to_pdf_page_sizes(self, temp_image_file, tmp_path):
        """Test different page sizes."""
        engine = ConversionEngine()

        for page_size in ["A4", "Letter", "Original"]:
            output_pdf = tmp_path / f"output_{page_size}.pdf"
            result = engine.images_to_pdf([temp_image_file], output_pdf, page_size)

            assert result is True
            assert output_pdf.exists()

    def test_images_to_pdf_mixed_formats(self, tmp_path):
        """Test converting mixed image formats."""
        # Create test images in different formats
        jpg_path = tmp_path / "test.jpg"
        png_path = tmp_path / "test.png"

        img = Image.new("RGB", (100, 100), color="red")
        img.save(jpg_path, "JPEG")

        img_png = Image.new("RGB", (100, 100), color="blue")
        img_png.save(png_path, "PNG")

        engine = ConversionEngine()
        output_pdf = tmp_path / "mixed.pdf"

        result = engine.images_to_pdf([jpg_path, png_path], output_pdf, "A4")

        assert result is True
        assert output_pdf.exists()

    def test_pdf_to_images_all_pages(self, temp_pdf_file, tmp_path):
        """Test converting all PDF pages to images."""
        engine = ConversionEngine()
        output_dir = tmp_path / "images"

        result = engine.pdf_to_images(temp_pdf_file, output_dir, "jpg", 300)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(Path(p).exists() for p in result)

    def test_pdf_to_images_selective_pages(self, temp_pdf_file, tmp_path):
        """Test converting selective PDF pages."""
        engine = ConversionEngine()
        output_dir = tmp_path / "images"

        # Extract only page 1
        result = engine.pdf_to_images(temp_pdf_file, output_dir, "jpg", 300, [1])

        assert isinstance(result, list)
        assert len(result) == 1

    def test_pdf_to_images_formats(self, temp_pdf_file, tmp_path):
        """Test different output formats for PDF to images."""
        engine = ConversionEngine()

        for fmt in ["jpg", "png", "tiff"]:
            output_dir = tmp_path / fmt
            result = engine.pdf_to_images(temp_pdf_file, output_dir, fmt, 300)

            assert isinstance(result, list)
            assert len(result) > 0
            assert all(str(p).endswith(f".{fmt}") for p in result)

    def test_pdf_to_images_custom_dpi(self, temp_pdf_file, tmp_path):
        """Test PDF to images with custom DPI."""
        engine = ConversionEngine()
        output_dir = tmp_path / "images"

        result = engine.pdf_to_images(temp_pdf_file, output_dir, "jpg", 150)

        assert isinstance(result, list)
        assert len(result) > 0

    # ===== CONTENT QUALITY & CORRECTNESS TESTS =====

    def test_images_to_pdf_content_quality(self, tmp_path):
        """Test that PDF pages contain correct image content with proper colors."""
        # Create test images with specific colors
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Red, Green, Blue
        image_paths = []

        for i, color in enumerate(colors):
            img_path = tmp_path / f"test_color_{i}.jpg"
            img = Image.new("RGB", (200, 200), color=color)
            img.save(img_path, quality=95)
            image_paths.append(img_path)

        # Convert to PDF
        engine = ConversionEngine()
        output_pdf = tmp_path / "quality_test.pdf"
        result = engine.images_to_pdf(image_paths, output_pdf, "A4")
        assert result is True

        # Verify PDF content
        doc = fitz.open(str(output_pdf))
        assert len(doc) == len(colors), "PDF should have correct number of pages"

        for page_num, expected_color in enumerate(colors):
            page = doc[page_num]
            # Render page to image
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Get dominant color from center of image (avoid white margins)
            center_region = img.crop(
                (pix.width // 4, pix.height // 4, 3 * pix.width // 4, 3 * pix.height // 4)
            )
            avg_color = tuple(int(v) for v in ImageStat.Stat(center_region).mean)

            # Check if color is close to expected (allow some compression loss)
            tolerance = 30
            for i in range(3):
                assert abs(avg_color[i] - expected_color[i]) < tolerance, (
                    f"Page {page_num} color mismatch: expected {expected_color}, got {avg_color}"
                )

        doc.close()

    def test_images_to_pdf_page_dimensions(self, tmp_path):
        """Test that PDF pages have correct dimensions based on page size."""
        # Create a test image
        img_path = tmp_path / "test_dimensions.jpg"
        img = Image.new("RGB", (800, 600), color="blue")
        img.save(img_path)

        engine = ConversionEngine()

        # Test A4 dimensions (595 x 842 points)
        output_a4 = tmp_path / "test_a4.pdf"
        engine.images_to_pdf([img_path], output_a4, "A4")

        doc = fitz.open(str(output_a4))
        page = doc[0]
        # A4 in points: 595.28 x 841.89
        assert abs(page.rect.width - 595.28) < 1, f"A4 width incorrect: {page.rect.width}"
        assert abs(page.rect.height - 841.89) < 1, f"A4 height incorrect: {page.rect.height}"
        doc.close()

        # Test Letter dimensions (612 x 792 points)
        output_letter = tmp_path / "test_letter.pdf"
        engine.images_to_pdf([img_path], output_letter, "Letter")

        doc = fitz.open(str(output_letter))
        page = doc[0]
        # Letter in points: 612 x 792
        assert abs(page.rect.width - 612) < 1, f"Letter width incorrect: {page.rect.width}"
        assert abs(page.rect.height - 792) < 1, f"Letter height incorrect: {page.rect.height}"
        doc.close()

        # Test Original dimensions (should match image aspect ratio)
        output_original = tmp_path / "test_original.pdf"
        engine.images_to_pdf([img_path], output_original, "Original")

        doc = fitz.open(str(output_original))
        page = doc[0]
        # Should maintain 800:600 aspect ratio (4:3)
        aspect_ratio = page.rect.width / page.rect.height
        expected_ratio = 800 / 600
        assert abs(aspect_ratio - expected_ratio) < 0.01, (
            f"Original aspect ratio incorrect: {aspect_ratio} vs {expected_ratio}"
        )
        doc.close()

    def test_pdf_to_images_content_preservation(self, tmp_path):
        """Test that extracted images preserve original content."""
        # Create test PDF with known content
        original_color = (128, 64, 192)  # Purple
        img_path = tmp_path / "original.jpg"
        original_img = Image.new("RGB", (300, 300), color=original_color)
        original_img.save(img_path)

        # Convert to PDF
        engine = ConversionEngine()
        pdf_path = tmp_path / "test.pdf"
        engine.images_to_pdf([img_path], pdf_path, "A4")

        # Extract back to image
        output_dir = tmp_path / "extracted"
        extracted_paths = engine.pdf_to_images(pdf_path, output_dir, "png", 300)

        assert len(extracted_paths) == 1

        # Load extracted image
        extracted_img = Image.open(extracted_paths[0])

        # Get dominant color from center
        width, height = extracted_img.size
        center_region = extracted_img.crop(
            (width // 4, height // 4, 3 * width // 4, 3 * height // 4)
        )
        avg_color = tuple(int(v) for v in ImageStat.Stat(center_region).mean)

        # Verify color is preserved (with tolerance for compression)
        tolerance = 50
        for i in range(3):
            assert abs(avg_color[i] - original_color[i]) < tolerance, (
                f"Color not preserved: expected {original_color}, got {avg_color}"
            )

    def test_pdf_to_images_resolution_quality(self, temp_pdf_file, tmp_path):
        """Test that extracted images have correct resolution based on DPI."""
        engine = ConversionEngine()

        # Test different DPI settings
        dpi_settings = [150, 300, 600]

        for dpi in dpi_settings:
            output_dir = tmp_path / f"dpi_{dpi}"
            extracted = engine.pdf_to_images(temp_pdf_file, output_dir, "png", dpi)

            assert len(extracted) > 0

            # Check first extracted image resolution
            img = Image.open(extracted[0])
            width, height = img.size

            # Higher DPI should produce larger images
            # A4 at 150 DPI should be roughly 1240 x 1754 pixels
            # A4 at 300 DPI should be roughly 2480 x 3508 pixels
            expected_width = int(595 * dpi / 72)  # A4 width in points * DPI / 72

            # Allow 10% tolerance for scaling
            assert abs(width - expected_width) / expected_width < 0.15, (
                f"DPI {dpi}: width {width} not close to expected {expected_width}"
            )

    def test_images_to_pdf_multi_format_content(self, tmp_path):
        """Test that mixed format images (JPG, PNG) are correctly embedded in PDF."""
        # Create images in different formats with different content
        jpg_path = tmp_path / "test.jpg"
        png_path = tmp_path / "test.png"

        jpg_img = Image.new("RGB", (200, 200), color=(255, 100, 100))  # Reddish
        jpg_img.save(jpg_path, "JPEG", quality=90)

        png_img = Image.new("RGB", (200, 200), color=(100, 100, 255))  # Blueish
        png_img.save(png_path, "PNG")

        # Convert to PDF
        engine = ConversionEngine()
        output_pdf = tmp_path / "mixed_formats.pdf"
        result = engine.images_to_pdf([jpg_path, png_path], output_pdf, "A4")

        assert result is True

        # Verify both pages are in PDF and have different colors
        doc = fitz.open(str(output_pdf))
        assert len(doc) == 2

        colors_found = []
        for page_num in range(2):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Get center color
            center = img.crop(
                (pix.width // 3, pix.height // 3, 2 * pix.width // 3, 2 * pix.height // 3)
            )
            avg_color = tuple(int(v) for v in ImageStat.Stat(center).mean)
            colors_found.append(avg_color)

        doc.close()

        # First page should be reddish (R > B), second should be blueish (B > R)
        assert colors_found[0][0] > colors_found[0][2], "First page should be reddish"
        assert colors_found[1][2] > colors_found[1][0], "Second page should be blueish"

    def test_pdf_metadata_stripped(self, temp_image_file, tmp_path):
        """Test that generated PDFs don't contain unnecessary metadata."""
        engine = ConversionEngine()
        output_pdf = tmp_path / "metadata_test.pdf"

        engine.images_to_pdf([temp_image_file], output_pdf, "A4")

        doc = fitz.open(str(output_pdf))
        metadata = doc.metadata

        # Check that sensitive metadata is not present
        # Producer and creator are okay, but personal info should be stripped
        assert metadata.get("author", "") == "", "Author metadata should be empty"
        assert metadata.get("subject", "") == "", "Subject metadata should be empty"
        assert metadata.get("keywords", "") == "", "Keywords metadata should be empty"

        doc.close()


class TestPrivacyModule:
    """Test privacy/metadata stripping."""

    def test_strip_image_metadata(self, temp_image_file):
        """Test EXIF metadata stripping."""
        # Create test image
        img_with_exif = Image.new("RGB", (100, 100))

        # Strip metadata
        clean_img = strip_image_metadata(img_with_exif)

        # Verify no EXIF data
        assert clean_img.mode == img_with_exif.mode
        assert clean_img.size == img_with_exif.size
        assert not hasattr(clean_img, "info") or not clean_img.info

    def test_ensure_rgb_mode_rgba(self):
        """Test RGBA to RGB conversion."""
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        rgb_img = ensure_rgb_mode(img)

        assert rgb_img.mode == "RGB"

    def test_ensure_rgb_mode_already_rgb(self):
        """Test RGB image remains RGB."""
        img = Image.new("RGB", (100, 100), color="red")
        rgb_img = ensure_rgb_mode(img)

        assert rgb_img.mode == "RGB"
        assert rgb_img == img  # Should be same object

    def test_ensure_rgb_mode_grayscale(self):
        """Test grayscale mode handling."""
        img = Image.new("L", (100, 100), color=128)
        result_img = ensure_rgb_mode(img)

        # Grayscale is PDF compatible, so it should remain as-is
        assert result_img.mode in ["L", "RGB"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
