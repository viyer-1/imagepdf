"""
Core conversion engines for Images <-> PDF operations.
Supports: JPG, JPEG, PNG, TIFF, TIF, BMP, WEBP
All conversions are privacy-focused and strip metadata.
"""

import io
from pathlib import Path
from typing import List, Union

import fitz  # PyMuPDF for PDF to image conversion
from PIL import Image
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..utils import get_logger
from .privacy import ensure_rgb_mode, strip_image_metadata


class ConversionEngine:
    """Handles bidirectional Image <-> PDF conversions with privacy features.

    Supported formats: JPG, JPEG, PNG, TIFF, TIF, BMP, WEBP
    Mixed format conversions supported (e.g., JPG + PNG + TIFF + BMP + WEBP -> PDF)
    """

    # Page size presets
    PAGE_SIZES = {
        "A4": A4,
        "Letter": letter,
        "Original": None,  # Will use image dimensions
    }

    @staticmethod
    def images_to_pdf(
        image_paths: List[Union[str, Path]], output_path: Union[str, Path], page_size: str = "A4"
    ) -> bool:
        """
        Convert multiple images to a single PDF file.
        Supports: JPG, JPEG, PNG, TIFF, TIF, BMP, WEBP (mixed formats allowed)
        All EXIF metadata is automatically stripped for privacy.

        Args:
            image_paths: List of paths to image files (any supported format)
            output_path: Path where PDF should be saved
            page_size: 'A4', 'Letter', or 'Original'

        Returns:
            True if successful, False otherwise
        """
        logger = get_logger()
        logger.info(
            f"Starting images_to_pdf conversion: {len(image_paths)} images -> {output_path}"
        )
        logger.debug(f"Page size: {page_size}, Input files: {[str(p) for p in image_paths]}")

        try:
            # Determine page size
            pdf_pagesize = ConversionEngine.PAGE_SIZES.get(page_size, A4)

            # Create PDF canvas with minimal metadata for privacy
            c = canvas.Canvas(str(output_path), pagesize=pdf_pagesize)
            # Strip metadata for privacy - set to empty strings
            c.setAuthor("")
            c.setTitle("")
            c.setSubject("")
            c.setKeywords([])

            for i, img_path in enumerate(image_paths):
                # Load image
                img = Image.open(img_path)

                # Strip metadata for privacy
                img = strip_image_metadata(img)

                # Ensure RGB mode for PDF compatibility
                img = ensure_rgb_mode(img)

                # Handle page sizing
                if page_size == "Original":
                    # Use first image dimensions for all pages
                    if i == 0:
                        pdf_pagesize = img.size
                        c.setPageSize(pdf_pagesize)
                    page_width, page_height = pdf_pagesize
                else:
                    page_width, page_height = pdf_pagesize

                # Convert to bytes for ReportLab
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="JPEG")
                img_byte_arr.seek(0)
                img_reader = ImageReader(img_byte_arr)

                # Draw image to fill entire page
                c.drawImage(img_reader, 0, 0, width=page_width, height=page_height)

                # Add new page for next image
                c.showPage()

            # Save PDF
            c.save()
            logger.info(f"Successfully created PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error converting images to PDF: {e}", exc_info=True)
            return False

    @staticmethod
    def pdf_to_images(
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        output_format: str = "jpg",
        dpi: int = 300,
        page_numbers: List[int] = None,
    ) -> List[Path]:
        """
        Convert PDF pages to individual image files.
        Metadata is stripped from output images.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory where images should be saved
            output_format: 'jpg', 'png', or 'tiff'
            dpi: Resolution for output images (default: 300)
            page_numbers: Optional list of page numbers to extract (1-indexed).
                         If None, extracts all pages.
                         Example: [1, 3, 5] extracts only pages 1, 3, and 5

        Returns:
            List of paths to created image files
        """
        logger = get_logger()
        logger.info(f"Starting pdf_to_images conversion: {pdf_path} -> {output_dir}")
        logger.debug(f"Format: {output_format}, DPI: {dpi}, Pages: {page_numbers or 'all'}")

        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            pdf_document = fitz.open(str(pdf_path))
            output_files = []

            pdf_name = Path(pdf_path).stem
            total_pages = len(pdf_document)

            # Determine which pages to extract
            if page_numbers is None:
                # Extract all pages
                pages_to_extract = range(total_pages)
            else:
                # Extract specific pages (convert from 1-indexed to 0-indexed)
                pages_to_extract = [p - 1 for p in page_numbers if 0 < p <= total_pages]

            for page_index in pages_to_extract:
                # Get page
                page = pdf_document[page_index]

                # Render page to image
                zoom = dpi / 72  # 72 is default DPI
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PIL Image
                if output_format == "jpg":
                    img_data = pix.tobytes("jpeg")
                elif output_format == "png":
                    img_data = pix.tobytes("png")
                elif output_format in ["tiff", "tif"]:
                    img_data = pix.tobytes("png")  # Convert via PNG first
                    output_format = "tiff"
                else:
                    img_data = pix.tobytes("jpeg")
                    output_format = "jpg"

                img = Image.open(io.BytesIO(img_data))

                # Strip metadata for privacy
                img = strip_image_metadata(img)

                # Save image (use actual page number in filename)
                output_file = output_dir / f"{pdf_name}_page_{page_index + 1:03d}.{output_format}"

                if output_format == "jpg":
                    img.save(output_file, quality=95)
                elif output_format == "tiff":
                    img.save(output_file, compression="tiff_lzw")
                else:
                    img.save(output_file)

                output_files.append(output_file)

            pdf_document.close()
            logger.info(f"Successfully created {len(output_files)} image(s) from PDF")
            return output_files

        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}", exc_info=True)
            return []
