# Image ↔ PDF Converter (Desktop Application)

A professional, privacy-focused desktop application for bidirectional conversion between images and PDF format. All processing happens locally — files never leave your computer.

## Key Features

- **Privacy First**: Automatically strips all EXIF metadata (GPS, device info, timestamps) from images.
- **Bidirectional Conversion**: Images → PDF and PDF → Images.
- **Multiple Formats**: JPG, PNG, TIFF, BMP, WEBP.
- **Local Processing**: No cloud uploads, no internet required for conversions.
- **Modern UI**: PyQt6 interface with thumbnail previews, drag-and-drop reordering, and Material Design-inspired styling.
- **Local REST API**: Programmatic access via a localhost API for automation.
- **Cross-Platform**: Windows, macOS, and Linux.

## Installation

```bash
cd desktop-app
pip install -r requirements.txt
```

## Running

```bash
python src/main.py
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
desktop-app/
├── src/
│   ├── main.py                    # Application entry point
│   ├── core/
│   │   ├── converters.py          # Conversion engine (images↔PDF)
│   │   └── privacy.py             # EXIF/metadata stripping
│   ├── ui/
│   │   └── main_window.py         # Main window, thumbnails, drag-drop
│   ├── api/
│   │   ├── local_api.py           # Local REST API
│   │   └── README.md              # API endpoint documentation
│   └── utils/
│       ├── config_manager.py      # App config loader
│       ├── icon_generator.py      # Programmatic icon generation
│       └── logger.py              # Rotating log system
├── config/
│   └── app_config.json            # App branding, window settings, UI params
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── test_converters.py         # Conversion engine tests
│   └── test_utils.py              # Utility module tests
├── build_scripts/                 # Cross-platform build system
│   ├── BUILD_INSTRUCTIONS.md      # Comprehensive build guide
│   └── GITHUB_ACTIONS_BUILD.md    # CI/CD cloud build guide
├── assets/
│   └── icon.png                   # Application icon
└── requirements.txt
```

## Architecture

### Core Conversion Engine (`src/core/converters.py`)

- **`images_to_pdf()`**: Converts multiple images to a single PDF using ReportLab. Supports A4, Letter, and Original (image dimensions) page sizes. Handles RGBA → RGB conversion. Automatically strips EXIF metadata.
- **`pdf_to_images()`**: Extracts PDF pages as images using PyMuPDF at configurable DPI (default 300). Supports selective page extraction via a 1-indexed page number list. Output formats: JPG, PNG, TIFF.

### Privacy Module (`src/core/privacy.py`)

- **`strip_image_metadata()`**: Reconstructs images with pixel data only, removing all EXIF data (GPS, device info, author, timestamps, camera settings).
- **`ensure_rgb_mode()`**: Converts RGBA/palette images to RGB for PDF compatibility.

### UI (`src/ui/main_window.py`)

- Horizontal split layout: thumbnail grid (left) + control pane (right).
- Drag-and-drop file adding and thumbnail reordering.
- Background conversion via `ConversionWorker` (QThread).
- FontAwesome icons, Material Design shadows/elevation.

### Local REST API (`src/api/local_api.py`)

A Flask-based REST API that runs on `localhost:5050`. Provides programmatic access to conversions while keeping all processing local. See [src/api/README.md](src/api/README.md) for endpoint documentation.

## Configuration

### App Config (`config/app_config.json`)

Centralized branding and UI settings: app name, company name, version, window dimensions, thumbnail size, control pane width. All build scripts read from this file.

## Building for Distribution

The `build_scripts/` directory contains a cross-platform build system supporting Windows (.exe installer), macOS (.dmg), Linux x86_64 (.AppImage), and Linux ARM/Raspberry Pi (.AppImage).

```bash
# Auto-detect platform and build
./build_scripts/build.sh          # Linux/macOS
build_scripts\build.bat           # Windows
```

For cloud-based builds without needing each platform's hardware, see the GitHub Actions workflow.

- [build_scripts/BUILD_INSTRUCTIONS.md](build_scripts/BUILD_INSTRUCTIONS.md) — Comprehensive build guide.
- [build_scripts/GITHUB_ACTIONS_BUILD.md](build_scripts/GITHUB_ACTIONS_BUILD.md) — CI/CD cloud builds.

## Log Files

Application logs are saved with automatic rotation (10 MB, 5 backups):

- **Linux**: `~/.local/share/jpg-pdf-converter/logs/app.log`
- **macOS**: `~/Library/Application Support/JPG PDF Converter/logs/app.log`
- **Windows**: `%LOCALAPPDATA%\Image-PDF Open Source\JPG PDF Converter\logs\app.log`

## License
Released under the **MIT License**.
