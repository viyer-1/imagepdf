#!/bin/bash
# Build script for JPG2PDF Converter - macOS
# This script creates a .app bundle and optionally a .dmg installer

set -e  # Exit on error

echo "========================================"
echo "JPG2PDF Converter - macOS Build Script"
echo "========================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or later from https://python.org"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Check if in virtual environment (optional but recommended)
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}WARNING: Not running in a virtual environment${NC}"
    echo "It's recommended to use a virtual environment for building"
    echo ""
    # Skip interactive prompt in CI environment
    if [[ -z "${CI}" ]]; then
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "CI environment detected, continuing..."
    fi
fi

# Install/upgrade build dependencies
echo "Installing build dependencies..."
pip3 install --upgrade pip
pip3 install pyinstaller
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to install dependencies${NC}"
    exit 1
fi

# Get app name from config for cleaning
APP_NAME_TEMP=$(python3 build_scripts/read_config.py branding.app_name 2>/dev/null || echo "JPG2PDF Converter")

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build
rm -rf dist/JPG2PDF-Converter
rm -rf "dist/$APP_NAME_TEMP.app"
rm -rf "dist/Image ↔ PDF Converter.app"  # Clean old name too

# Build with PyInstaller
echo ""
echo "Building .app bundle with PyInstaller..."
pyinstaller --clean build_scripts/macos/jpg2pdf_macos.spec

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: PyInstaller build failed${NC}"
    exit 1
fi

# Get app name from config
APP_NAME=$(python3 build_scripts/read_config.py branding.app_name)
VERSION=$(python3 build_scripts/read_config.py version.full)
APP_NAME_EXEC=$(python3 build_scripts/read_config.py branding.app_name_executable)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Application location: dist/$APP_NAME.app"
echo ""

# Ask if user wants to create DMG (or auto-create in CI)
if [[ -n "${CI}" ]]; then
    echo "CI environment detected, creating DMG automatically..."
    CREATE_DMG=true
else
    read -p "Do you want to create a .dmg installer? (requires create-dmg) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CREATE_DMG=true
    else
        CREATE_DMG=false
    fi
fi

if [[ "$CREATE_DMG" == "true" ]]; then
    if ! command -v create-dmg &> /dev/null; then
        echo -e "${YELLOW}create-dmg is not installed${NC}"
        echo "Installing via Homebrew..."
        if ! command -v brew &> /dev/null; then
            echo -e "${RED}ERROR: Homebrew is not installed${NC}"
            echo "Please install Homebrew from https://brew.sh"
            echo "Then run: brew install create-dmg"
            exit 1
        fi
        brew install create-dmg
    fi

    echo ""
    echo "Creating DMG installer..."

    # Create dist/macos directory if it doesn't exist
    mkdir -p dist/macos

    # DMG file name
    DMG_NAME="${APP_NAME_EXEC}-${VERSION}-macOS.dmg"

    # Remove old DMG if exists
    rm -f "dist/macos/$DMG_NAME"

    # Create DMG (simplified, without icon positioning which fails in CI)
    if [[ -n "${CI}" ]]; then
        # CI mode: Simplified DMG without AppleScript positioning
        create-dmg \
            --volname "$APP_NAME" \
            --window-size 600 400 \
            --app-drop-link 425 120 \
            --no-internet-enable \
            "dist/macos/$DMG_NAME" \
            "dist/$APP_NAME.app"
    else
        # Local mode: Full DMG with custom positioning
        create-dmg \
            --volname "$APP_NAME" \
            --volicon "assets/icon.png" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "$APP_NAME.app" 175 120 \
            --hide-extension "$APP_NAME.app" \
            --app-drop-link 425 120 \
            --no-internet-enable \
            "dist/macos/$DMG_NAME" \
            "dist/$APP_NAME.app"
    fi

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}DMG installer created successfully!${NC}"
        echo "Location: dist/macos/$DMG_NAME"
    else
        echo -e "${YELLOW}Warning: DMG creation had issues but may have succeeded${NC}"
        echo "Check: dist/macos/JPG2PDF-Converter-1.0.0-macOS.dmg"
    fi
fi

echo ""
echo "To test the app, run:"
echo "  open 'dist/JPG2PDF Converter.app'"
echo ""
echo "To sign the app for distribution (requires Apple Developer account):"
echo "  codesign --force --deep --sign 'Developer ID Application: Your Name' 'dist/JPG2PDF Converter.app'"
echo "  codesign --verify --verbose 'dist/JPG2PDF Converter.app'"
echo ""
