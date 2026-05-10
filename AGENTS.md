# Image ↔ PDF Converter (Open Source)

This file provides guidance to agents when working with code in this repository.

## Version Control Workflow

1. Make requested changes to the code.
2. Show the user what was changed and ask for approval if needed.
3. Once approved, commit the changes with a descriptive commit message.
4. Push the commits to the remote repository when requested.

## Project Overview

Image ↔ PDF Converter - A privacy-focused file conversion application.
All features are unlocked and available to all users. No licensing or billing systems are present.

## Project Structure

### Desktop Application
```
desktop-app/
├── src/
│   ├── main.py                    # Application entry point
│   ├── ui/
│   │   └── main_window.py         # Main window with thumbnail grid & drag-drop
│   ├── core/
│   │   ├── converters.py          # Bidirectional conversion engine
│   │   └── privacy.py             # EXIF/metadata stripping utilities
│   ├── api/
│   │   ├── local_api.py           # Local REST API (localhost-only)
│   │   └── README.md              # API endpoint documentation
│   └── utils/
│       ├── config_manager.py      # App config loader
│       ├── icon_generator.py      # Programmatic icon generation
│       └── logger.py              # Rotating log system
├── config/
│   └── app_config.json            # App branding, window settings, UI params
├── build_scripts/                 # Cross-platform build system
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── test_converters.py         # Conversion engine tests
│   └── test_utils.py              # Utility module tests
├── assets/
│   └── icon.png                   # Application icon
├── CHANGELOG.md                   # Version history
├── requirements.txt
└── README.md
```

### Landing Page
- `landing-page/` - Website for the application (HTML/CSS).

## Running the Application

```bash
cd desktop-app
pip install -r requirements.txt
python src/main.py
```

## Development Workflow

1. **Lint with Ruff:**
   ```bash
   cd desktop-app
   ruff check src/
   ```

2. **Run Tests:**
   ```bash
   pytest tests/ -v
   ```

3. **Commit Changes:**

**Quick Command (all checks):**
```bash
ruff check src/ && pytest tests/ -v && echo "✓ Ready to commit"
```
