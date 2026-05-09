"""
Simple icon generator for the application.
Creates a basic PNG icon programmatically.
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw


def generate_app_icon(size: int = 256) -> bytes:
    """
    Generate a simple application icon.

    Args:
        size: Icon size in pixels (default: 256x256)

    Returns:
        PNG icon data as bytes
    """
    # Create image with gradient background
    img = Image.new("RGB", (size, size), color="#3498db")
    draw = ImageDraw.Draw(img)

    # Draw a simple document icon shape
    padding = size // 8
    doc_left = padding
    doc_right = size - padding
    doc_top = padding
    doc_bottom = size - padding

    # Background rectangle (document)
    draw.rectangle(
        [(doc_left, doc_top), (doc_right, doc_bottom)],
        fill="white",
        outline="#2c3e50",
        width=size // 40,
    )

    # Draw folded corner
    corner_size = size // 6
    corner_points = [
        (doc_right - corner_size, doc_top),
        (doc_right, doc_top + corner_size),
        (doc_right - corner_size, doc_top + corner_size),
    ]
    draw.polygon(corner_points, fill="#ecf0f1", outline="#2c3e50")

    # Draw lines to represent text
    line_padding = size // 5
    line_spacing = size // 12
    line_width = size // 30

    for i in range(3):
        y = doc_top + line_padding + (i * line_spacing)
        draw.rectangle(
            [
                (doc_left + line_padding, y),
                (doc_right - line_padding - (i * size // 20), y + line_width),
            ],
            fill="#3498db",
        )

    # Draw PDF text
    try:
        # Try to use default font, or just skip text if not available
        text = "PDF"

        # Calculate text position (center bottom)
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (size - text_width) // 2
        text_y = size - padding - text_height

        draw.text((text_x, text_y), text, fill="#e74c3c")
    except Exception:
        # If font fails, skip text
        pass

    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def save_app_icon(output_path: Path, size: int = 256):
    """
    Generate and save application icon to file.

    Args:
        output_path: Path where to save the icon
        size: Icon size in pixels
    """
    icon_data = generate_app_icon(size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(icon_data)


if __name__ == "__main__":
    # Generate icon when run directly
    icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
    save_app_icon(icon_path, 256)
    print(f"Icon generated at: {icon_path}")
