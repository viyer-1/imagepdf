#!/bin/bash
# Universal build script for JPG2PDF Converter
# Automatically detects platform and calls appropriate build script

set -e

echo "============================================"
echo "JPG2PDF Converter - Universal Build Script"
echo "============================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    # Detect architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "x86_64" ]]; then
        PLATFORM="linux_x86"
    elif [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "armv7l" ]] || [[ "$ARCH" == "armhf" ]]; then
        PLATFORM="linux_arm"
    else
        echo -e "${RED}ERROR: Unsupported Linux architecture: $ARCH${NC}"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PLATFORM="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
    PLATFORM="windows"
else
    echo -e "${RED}ERROR: Unsupported operating system: $OSTYPE${NC}"
    exit 1
fi

echo -e "${BLUE}Detected platform: $PLATFORM${NC}"
echo ""

# Display build information
echo "Build configuration:"
echo "  OS: $OS"
echo "  Platform: $PLATFORM"
if [[ "$OS" == "linux" ]]; then
    echo "  Architecture: $ARCH"
fi
echo ""

# Confirm before building
read -p "Proceed with build? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled"
    exit 0
fi

echo ""
echo "Starting build..."
echo ""

# Call platform-specific build script
case $PLATFORM in
    linux_x86)
        if [ ! -f "build_scripts/linux_x86/build_linux_x86.sh" ]; then
            echo -e "${RED}ERROR: Linux x86 build script not found${NC}"
            exit 1
        fi
        bash build_scripts/linux_x86/build_linux_x86.sh
        ;;
    linux_arm)
        if [ ! -f "build_scripts/linux_arm/build_linux_arm.sh" ]; then
            echo -e "${RED}ERROR: Linux ARM build script not found${NC}"
            exit 1
        fi
        bash build_scripts/linux_arm/build_linux_arm.sh
        ;;
    macos)
        if [ ! -f "build_scripts/macos/build_macos.sh" ]; then
            echo -e "${RED}ERROR: macOS build script not found${NC}"
            exit 1
        fi
        bash build_scripts/macos/build_macos.sh
        ;;
    windows)
        if [ ! -f "build_scripts/windows/build_windows.bat" ]; then
            echo -e "${RED}ERROR: Windows build script not found${NC}"
            exit 1
        fi
        # On Windows with bash (Git Bash, WSL, etc.), call the batch file
        cmd //c "build_scripts\\windows\\build_windows.bat"
        ;;
    *)
        echo -e "${RED}ERROR: Unknown platform: $PLATFORM${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Universal build completed!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Check the appropriate distribution directory for your platform:"
echo "  Windows: dist/windows/"
echo "  macOS: dist/macos/"
echo "  Linux x86: dist/linux_x86/"
echo "  Linux ARM: dist/linux_arm/"
echo ""
