#!/bin/bash
# Build script for Image-PDF Converter - Linux x86_64
# Creates both AppImage and tar.gz distributions
# Reads branding from config/app_config.json

set -e  # Exit on error

echo "=============================================="
echo "Image-PDF Converter - Linux x86_64 Build Script"
echo "=============================================="
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
ARCH="x86_64"

echo "Building: $APP_NAME_DISPLAY v$APP_VERSION"
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

# Install/upgrade build dependencies
echo "Installing build dependencies..."
pip3 install --upgrade pip
pip3 install pyinstaller
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to install dependencies${NC}"
    exit 1
fi

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf build
rm -rf dist/$APP_NAME
rm -rf dist/linux_x86

# Build with PyInstaller
echo ""
echo "Building executable with PyInstaller..."
pyinstaller --clean \
    --name $APP_NAME \
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
    --icon assets/icon.png \
    src/main.py

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: PyInstaller build failed${NC}"
    exit 1
fi

mkdir -p dist/linux_x86

# ============================================
# Create tar.gz distribution
# ============================================
echo ""
echo "Creating tar.gz distribution..."

TAR_DIR="$APP_NAME-$APP_VERSION-linux-$ARCH"
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
JPG2PDF Converter v$APP_VERSION
================================

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
- Linux x86_64 (64-bit)
- glibc 2.17 or later
- X11 or Wayland display server

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
Exec=/path/to/$APP_NAME-$APP_VERSION-linux-$ARCH/run.sh
Icon=/path/to/$APP_NAME-$APP_VERSION-linux-$ARCH/assets/icon.png
Terminal=false
Categories=Graphics;Office;Utility;
Keywords=pdf;jpg;png;tiff;convert;image;
EOF

# Create the tar.gz
cd dist
tar -czf "linux_x86/$APP_NAME-$APP_VERSION-linux-$ARCH.tar.gz" "$TAR_DIR"
cd ..

echo -e "${GREEN}tar.gz created: dist/linux_x86/$APP_NAME-$APP_VERSION-linux-$ARCH.tar.gz${NC}"

# ============================================
# Create AppImage
# ============================================
echo ""
echo "Creating AppImage..."

# Download appimagetool if not present
if [ ! -f "build_scripts/linux_x86/appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
        -O "build_scripts/linux_x86/appimagetool-x86_64.AppImage"
    chmod +x "build_scripts/linux_x86/appimagetool-x86_64.AppImage"
fi

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
export LD_LIBRARY_PATH="${HERE}/usr/lib/:${HERE}/usr/lib/i386-linux-gnu/:${HERE}/usr/lib/x86_64-linux-gnu/:${HERE}/usr/lib32/:${HERE}/usr/lib64/:${HERE}/lib/:${HERE}/lib/i386-linux-gnu/:${HERE}/lib/x86_64-linux-gnu/:${HERE}/lib32/:${HERE}/lib64/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/share/pyshared/${PYTHONPATH:+:$PYTHONPATH}"
export XDG_DATA_DIRS="${HERE}/usr/share/${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
export PERLLIB="${HERE}/usr/share/perl5/:${HERE}/usr/lib/perl5/${PERLLIB:+:$PERLLIB}"
export GSETTINGS_SCHEMA_DIR="${HERE}/usr/share/glib-2.0/schemas/${GSETTINGS_SCHEMA_DIR:+:$GSETTINGS_SCHEMA_DIR}"
export QT_PLUGIN_PATH="${HERE}/usr/lib/qt6/plugins/:${HERE}/usr/lib/x86_64-linux-gnu/qt6/plugins/:${HERE}/usr/lib64/qt6/plugins/:${HERE}/usr/lib/qt5/plugins/:${HERE}/usr/lib/x86_64-linux-gnu/qt5/plugins/:${HERE}/usr/lib64/qt5/plugins/${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"
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
Keywords=pdf;jpg;png;tiff;convert;image;
EOF

# Copy desktop file to standard location
cp "$APPDIR/jpg2pdf-converter.desktop" "$APPDIR/usr/share/applications/"

# Copy icon
cp assets/icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/jpg2pdf-converter.png"
cp assets/icon.png "$APPDIR/jpg2pdf-converter.png"
cp assets/icon.png "$APPDIR/.DirIcon"

# Build AppImage
ARCH=$ARCH build_scripts/linux_x86/appimagetool-x86_64.AppImage "$APPDIR" "dist/linux_x86/$APP_NAME-$APP_VERSION-$ARCH.AppImage"

if [ $? -eq 0 ]; then
    chmod +x "dist/linux_x86/$APP_NAME-$APP_VERSION-$ARCH.AppImage"
    echo -e "${GREEN}AppImage created: dist/linux_x86/$APP_NAME-$APP_VERSION-$ARCH.AppImage${NC}"
else
    echo -e "${YELLOW}Warning: AppImage creation had issues${NC}"
fi

# ============================================
# Summary
# ============================================
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo "Distribution files created in: dist/linux_x86/"
echo ""
echo "1. AppImage (recommended for users):"
echo "   dist/linux_x86/$APP_NAME-$APP_VERSION-$ARCH.AppImage"
echo "   Usage: chmod +x *.AppImage && ./*.AppImage"
echo ""
echo "2. tar.gz (portable):"
echo "   dist/linux_x86/$APP_NAME-$APP_VERSION-linux-$ARCH.tar.gz"
echo "   Usage: tar -xzf *.tar.gz && cd $APP_NAME-*/ && ./run.sh"
echo ""
echo "File sizes:"
ls -lh dist/linux_x86/
echo ""
