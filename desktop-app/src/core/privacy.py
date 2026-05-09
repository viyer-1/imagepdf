"""
Privacy utilities for handling sensitive document metadata.
Ensures all EXIF and metadata is stripped from files.
"""

from PIL import Image


def strip_image_metadata(image: Image.Image) -> Image.Image:
    """
    Remove all EXIF metadata from an image for privacy.
    This includes GPS location, device info, author data, timestamps, etc.

    Args:
        image: PIL Image object

    Returns:
        New PIL Image with only pixel data, no metadata
    """
    # Extract pixel data
    data = list(image.getdata())

    # Create new image with same mode and size but no metadata
    clean_image = Image.new(image.mode, image.size)
    clean_image.putdata(data)

    return clean_image


def ensure_rgb_mode(image: Image.Image) -> Image.Image:
    """
    Convert image to RGB mode if needed (PDF compatibility).

    Args:
        image: PIL Image object

    Returns:
        RGB mode PIL Image
    """
    if image.mode == "RGBA" or image.mode not in ["RGB", "L"]:
        return image.convert("RGB")
    return image
