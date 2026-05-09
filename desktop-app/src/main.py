#!/usr/bin/env python3
"""
Image <-> PDF Converter Desktop Application

A professional, privacy-focused desktop app for converting between Image and PDF formats. All conversions strip metadata to protect user privacy.
"""

import sys
from pathlib import Path

# Add parent directory to Python path to enable package imports
# This allows running from either: python main.py (from src/) or python src/main.py (from desktop-app/)
src_dir = Path(__file__).parent
parent_dir = src_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# ruff: noqa: E402
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.utils import get_config_manager, get_logger


def run_smoke_test() -> int:
    """Headless smoke test for CI/CD binary validation.

    Uses Qt's offscreen platform (no display needed) to verify:
    1. Qt initialises correctly in the packaged binary
    2. The conversion engine imports and runs end-to-end
    3. images_to_pdf and pdf_to_images produce valid output

    Writes a log to $RUNNER_TEMP/smoke_test.log (or the system temp dir)
    so results are visible even on Windows where stdout may be suppressed
    by the windowed binary.

    Returns 0 on success, 1 on failure.
    """
    import contextlib
    import os
    import tempfile
    import traceback

    from PIL import Image as PILImage

    # Qt's offscreen platform renders to memory buffers — no display required.
    # Must be set before QApplication is constructed.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    log_dir = os.environ.get("RUNNER_TEMP", tempfile.gettempdir())
    log_path = Path(log_dir) / "smoke_test.log"
    log_lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        log_lines.append(msg)

    try:
        log("[smoke-test] --- Binary smoke test starting ---")

        log("[smoke-test] 1/3 Initialising Qt (offscreen)...")
        QApplication(sys.argv)
        log("[smoke-test] 1/3 Qt OK")

        log("[smoke-test] 2/3 Importing conversion engine...")
        from src.core.converters import ConversionEngine

        engine = ConversionEngine()
        log("[smoke-test] 2/3 ConversionEngine OK")

        log("[smoke-test] 3/3 Running end-to-end conversion...")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Create a minimal synthetic test image (no file I/O from user)
            img = PILImage.new("RGB", (200, 200), color=(100, 150, 200))
            img_path = tmp / "smoke.jpg"
            img.save(str(img_path), "JPEG")

            # images → PDF
            pdf_path = tmp / "smoke.pdf"
            ok = engine.images_to_pdf([img_path], pdf_path, page_size="A4")
            if not ok or not pdf_path.exists():
                log("[smoke-test] FAILED: images_to_pdf returned False or produced no file")
                return 1
            log(f"[smoke-test]   images_to_pdf OK ({pdf_path.stat().st_size} bytes)")

            # PDF → images
            out_dir = tmp / "pages"
            out_dir.mkdir()
            pages = engine.pdf_to_images(pdf_path, out_dir, output_format="jpg")
            if not pages or not Path(pages[0]).exists():
                log("[smoke-test] FAILED: pdf_to_images returned no pages")
                return 1
            log(f"[smoke-test]   pdf_to_images OK ({len(pages)} page(s))")

        log("[smoke-test] 3/3 Conversion round-trip OK")
        log("[smoke-test] --- PASSED ---")
        return 0

    except Exception as e:
        log(f"[smoke-test] FAILED with exception: {e}")
        log(traceback.format_exc())
        return 1

    finally:
        with contextlib.suppress(OSError):
            log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def main():
    """Application entry point."""
    # Initialize logger and config
    logger = get_logger()
    config = get_config_manager()
    logger.info("Initializing application...")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(config.get_app_setting("branding", "app_name_short", default="Image-PDF"))
    app.setOrganizationName(config.get_app_setting("branding", "company_name", default="Image-PDF Open Source"))
    app.setApplicationVersion(config.get_app_setting("version", "full", default="1.1.0-oss"))

    # Set application icon
    icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    try:
        logger.info("Creating main window...")
        window = MainWindow()
        logger.info(f"Main window created: {window.windowTitle()}")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        sys.exit(run_smoke_test())
    main()
