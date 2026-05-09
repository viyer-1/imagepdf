#!/bin/bash
# Build script for Image-PDF Converter - Linux ARM (Raspberry Pi)
# Creates both AppImage and tar.gz distributions for ARM architecture
# Reads branding from config/app_config.json

set -e  # Exit on error

echo "==============================================="
echo "Image-PDF Converter - Linux ARM Build Script"
echo "==============================================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."
cd "$PROJECT_ROOT"

# Read configuration from app_config.json
echo "Reading configuration..."
APP_NAME=$(python3 build_scripts/read_config.py branding.app_name_executable)
APP_NAME_DISPLAY=$(python3 build_scripts/read_config.py branding.app_name)
APP_VERSION=$(python3 build_scripts/read_config.py version.full)
COMPANY_NAME=$(python3 build_scripts/read_config.py branding.company_name)

echo "Building: $APP_NAME_DISPLAY v$APP_VERSION"
echo ""

# Detect ARM architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    ARCH_NAME="aarch64"
    APPIMAGE_ARCH="aarch64"
elif [[ "$ARCH" == "armv7l" ]] || [[ "$ARCH" == "armhf" ]]; then
    ARCH_NAME="armhf"
    APPIMAGE_ARCH="armhf"
else
    echo "ERROR: Unsupported ARM architecture: $ARCH"
    echo "This script supports: aarch64 (64-bit) and armv7l/armhf (32-bit)"
    exit 1
fi

echo "Detected architecture: $ARCH_NAME"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed${NC}"
    echo "Install with: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Check for Raspberry Pi OS specific requirements
# NOTE: System packages are NOT installed to avoid conflicts with venv
# User should have PyQt6 installed via pip in their venv
if [ -f /etc/rpi-issue ]; then
    echo "Raspberry Pi OS detected"
    echo "Checking system dependencies..."

    # Only check for essential X11 libraries (don't install Python packages from apt)
    if ! dpkg -l | grep -q libxcb-xinerama0; then
        echo -e "${YELLOW}Note: libxcb-xinerama0 may be needed for Qt6${NC}"
        echo "Install with: sudo apt-get install libxcb-xinerama0"
    fi
fi

# Install/upgrade build dependencies
echo ""
echo "Installing build dependencies..."

# Verify we're in a venv to avoid polluting system packages
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}WARNING: Not in a virtual environment!${NC}"
    echo "Recommended: Activate your venv first"
    echo "Example: source ~/.venvs/main/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller
python3 -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to install dependencies${NC}"
    exit 1
fi

echo "Using Python environment: $VIRTUAL_ENV"
echo ""

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build
rm -rf dist/$APP_NAME
rm -rf dist/linux_arm

# Build with PyInstaller
echo ""
echo "Building executable with PyInstaller..."
echo "Note: This may take longer on Raspberry Pi hardware..."
echo "Excluding unnecessary ML/data science libraries to reduce size..."

pyinstaller --clean \
    --name "$APP_NAME" \
    --onedir \
    --windowed \
    --add-data "config:config" \
    --add-data "assets:assets" \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import PIL._imaging \
    --hidden-import reportlab.pdfgen.canvas \
    --hidden-import fitz \
    --hidden-import flask \
    --hidden-import werkzeug \
    --exclude-module torch \
    --exclude-module tensorflow \
    --exclude-module scipy \
    --exclude-module pandas \
    --exclude-module sklearn \
    --exclude-module scikit-learn \
    --exclude-module matplotlib \
    --exclude-module numpy.testing \
    --exclude-module pytest \
    --exclude-module pytest-qt \
    --exclude-module pytest-cov \
    --exclude-module cv2 \
    --exclude-module tkinter \
    --exclude-module test \
    --exclude-module unittest \
    --exclude-module IPython \
    --exclude-module jupyter \
    --exclude-module notebook \
    --exclude-module babel \
    --exclude-module jinja2 \
    --exclude-module torchvision \
    --exclude-module onnxruntime \
    --exclude-module transformers \
    --exclude-module pydantic \
    --exclude-module imageio \
    --exclude-module imageio_ffmpeg \
    --exclude-module pyarrow \
    --exclude-module fsspec \
    --exclude-module regex \
    --exclude-module soundfile \
    --exclude-module rdflib \
    --exclude-module jsonschema \
    --icon assets/icon.png \
    src/main.py

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: PyInstaller build failed${NC}"
    exit 1
fi

mkdir -p dist/linux_arm

# ============================================
# Create tar.gz distribution
# ============================================
echo ""
echo "Creating tar.gz distribution..."

TAR_DIR="$APP_NAME-$APP_VERSION-linux-$ARCH_NAME"
mkdir -p "dist/$TAR_DIR"

# Copy application files
cp -r dist/$APP_NAME/* "dist/$TAR_DIR/"

# Create launcher script
cat > "dist/$TAR_DIR/run.sh" << 'EOF'
#!/bin/bash
# Launcher script for JPG2PDF Converter

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
./$APP_NAME "$@"
EOF

# Replace APP_NAME placeholder
sed -i "s/\$APP_NAME/$APP_NAME/g" "dist/$TAR_DIR/run.sh"
chmod +x "dist/$TAR_DIR/run.sh"

# Create README
cat > "dist/$TAR_DIR/README.txt" << EOF
JPG2PDF Converter v$APP_VERSION - ARM Edition
==============================================

This is the ARM version built for Raspberry Pi and other ARM-based Linux systems.
Architecture: $ARCH_NAME

INSTALLATION
------------
1. Extract this archive to any location
2. Run: ./run.sh

OR create a desktop shortcut:
1. Copy jpg2pdf-converter.desktop to ~/.local/share/applications/
2. Edit the Exec= and Icon= paths to point to your installation directory

RUNNING
-------
./run.sh

REQUIREMENTS
------------
- Linux ARM ($ARCH_NAME)
- Raspberry Pi OS (Bookworm or later) or compatible ARM Linux distribution
- X11 or Wayland display server
- Recommended: Raspberry Pi 3 or newer for optimal performance

RASPBERRY PI NOTES
------------------
- Tested on Raspberry Pi 3B+, 4, and 5
- For best performance, use Raspberry Pi 4 or newer
- Ensure your system is up to date: sudo apt-get update && sudo apt-get upgrade
- If you encounter graphics issues, ensure OpenGL is enabled: sudo raspi-config

UNINSTALLATION
--------------
Simply delete the extracted folder.

SUPPORT
-------
Visit: https://yourwebsite.com
Email: support@yourwebsite.com

COPYRIGHT
---------
Copyright © 2026 Your Company Name. All rights reserved.
EOF

# Create desktop file template
cat > "dist/$TAR_DIR/jpg2pdf-converter.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=JPG2PDF Converter
Comment=Convert images to PDF and PDF to images with privacy protection
Exec=/path/to/$APP_NAME-$APP_VERSION-linux-$ARCH_NAME/run.sh
Icon=/path/to/$APP_NAME-$APP_VERSION-linux-$ARCH_NAME/assets/icon.png
Terminal=false
Categories=Graphics;Office;Utility;
Keywords=pdf;jpg;png;tiff;convert;image;raspberry pi;
EOF

# Create the tar.gz
cd dist
tar -czf "linux_arm/$APP_NAME-$APP_VERSION-linux-$ARCH_NAME.tar.gz" "$TAR_DIR"
cd ..

echo -e "${GREEN}tar.gz created: dist/linux_arm/$APP_NAME-$APP_VERSION-linux-$ARCH_NAME.tar.gz${NC}"

# ============================================
# Create AppImage
# ============================================
echo ""
echo "Creating AppImage..."

# Download appropriate appimagetool for ARM
APPIMAGETOOL="build_scripts/linux_arm/appimagetool-$APPIMAGE_ARCH.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool for $APPIMAGE_ARCH..."
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-$APPIMAGE_ARCH.AppImage"

    wget -q "$APPIMAGETOOL_URL" -O "$APPIMAGETOOL" || {
        echo -e "${YELLOW}Warning: Could not download appimagetool for $APPIMAGE_ARCH${NC}"
        echo "AppImage creation will be skipped"
        echo "You can manually download it from: $APPIMAGETOOL_URL"
        SKIP_APPIMAGE=1
    }

    if [ -f "$APPIMAGETOOL" ]; then
        chmod +x "$APPIMAGETOOL"
    fi
fi

if [ "$SKIP_APPIMAGE" != "1" ]; then
    # Create AppDir structure
    APPDIR="dist/$APP_NAME.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

    # Copy application
    cp -r "dist/$APP_NAME"/* "$APPDIR/usr/bin/"

    # Create AppRun
    cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin/:${HERE}/usr/sbin/:${HERE}/usr/games/:${HERE}/bin/:${HERE}/sbin/${PATH:+:$PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib/:${HERE}/usr/lib/arm-linux-gnueabihf/:${HERE}/usr/lib/aarch64-linux-gnu/:${HERE}/lib/:${HERE}/lib/arm-linux-gnueabihf/:${HERE}/lib/aarch64-linux-gnu/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/share/pyshared/${PYTHONPATH:+:$PYTHONPATH}"
export XDG_DATA_DIRS="${HERE}/usr/share/${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
export PERLLIB="${HERE}/usr/share/perl5/:${HERE}/usr/lib/perl5/${PERLLIB:+:$PERLLIB}"
export GSETTINGS_SCHEMA_DIR="${HERE}/usr/share/glib-2.0/schemas/${GSETTINGS_SCHEMA_DIR:+:$GSETTINGS_SCHEMA_DIR}"
export QT_PLUGIN_PATH="${HERE}/usr/lib/qt6/plugins/:${HERE}/usr/lib/aarch64-linux-gnu/qt6/plugins/:${HERE}/usr/lib/arm-linux-gnueabihf/qt6/plugins/:${HERE}/usr/lib/qt5/plugins/:${HERE}/usr/lib/aarch64-linux-gnu/qt5/plugins/:${HERE}/usr/lib/arm-linux-gnueabihf/qt5/plugins/${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"
EXEC=$(grep -e '^Exec=.*' "${HERE}"/*.desktop | head -n 1 | cut -d "=" -f 2- | sed -e 's|%.||g')
exec ${EXEC} "$@"
EOF
    chmod +x "$APPDIR/AppRun"

    # Create desktop file
    cat > "$APPDIR/jpg2pdf-converter.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=JPG2PDF Converter
Comment=Convert images to PDF and PDF to images with privacy protection
Exec=$APP_NAME
Icon=jpg2pdf-converter
Terminal=false
Categories=Graphics;Office;Utility;
Keywords=pdf;jpg;png;tiff;convert;image;raspberry pi;
EOF

    # Copy desktop file to standard location
    cp "$APPDIR/jpg2pdf-converter.desktop" "$APPDIR/usr/share/applications/"

    # Copy icon
    cp assets/icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/jpg2pdf-converter.png"
    cp assets/icon.png "$APPDIR/jpg2pdf-converter.png"
    cp assets/icon.png "$APPDIR/.DirIcon"

    # Build AppImage
    echo "Building AppImage for architecture: $APPIMAGE_ARCH"

    # Export ARCH for appimagetool
    export ARCH="$APPIMAGE_ARCH"

    "$APPIMAGETOOL" "$APPDIR" "dist/linux_arm/$APP_NAME-$APP_VERSION-$ARCH_NAME.AppImage"

    if [ $? -eq 0 ]; then
        chmod +x "dist/linux_arm/$APP_NAME-$APP_VERSION-$ARCH_NAME.AppImage"
        echo -e "${GREEN}AppImage created: dist/linux_arm/$APP_NAME-$APP_VERSION-$ARCH_NAME.AppImage${NC}"
    else
        echo -e "${YELLOW}Warning: AppImage creation had issues${NC}"
        echo "You can still use the tar.gz distribution"
    fi

    unset ARCH
fi

# ============================================
# Summary
# ============================================
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo "Distribution files created in: dist/linux_arm/"
echo ""

if [ "$SKIP_APPIMAGE" != "1" ] && [ -f "dist/linux_arm/$APP_NAME-$APP_VERSION-$ARCH_NAME.AppImage" ]; then
    echo "1. AppImage (recommended for users):"
    echo "   dist/linux_arm/$APP_NAME-$APP_VERSION-$ARCH_NAME.AppImage"
    echo "   Usage: chmod +x *.AppImage && ./*.AppImage"
    echo ""
fi

echo "2. tar.gz (portable):"
echo "   dist/linux_arm/$APP_NAME-$APP_VERSION-linux-$ARCH_NAME.tar.gz"
echo "   Usage: tar -xzf *.tar.gz && cd $APP_NAME-*/ && ./run.sh"
echo ""

echo "File sizes:"
ls -lh dist/linux_arm/
echo ""

echo "NOTES FOR RASPBERRY PI USERS:"
echo "- This build has been optimized for Raspberry Pi"
echo "- Recommended: Raspberry Pi 3 or newer"
echo "- Ensure GPU acceleration is enabled for best performance"
echo ""
