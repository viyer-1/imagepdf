#!/bin/bash
################################################################################
# Cross-Platform Build Orchestrator for Distribution
#
# Purpose: Build installers for all platforms from a centralized build machine
# Use Case: Building on Raspberry Pi and distributing to users on various OSes
#
# This script handles:
# - Building native ARM Linux binaries on Raspberry Pi
# - Cross-platform builds where possible
# - Creating distribution-ready installers
# - Organizing output for release
#
# NOTE: Some platforms REQUIRE native builds:
# - Windows .exe: Must build on Windows (or use Wine/Docker - experimental)
# - macOS .app/.dmg: Must build on macOS (requires Apple Developer tools)
# - Linux ARM: Can build natively on Raspberry Pi (THIS MACHINE)
# - Linux x86_64: Can build on x86 Linux (requires Docker/VM from ARM)
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

# Load configuration
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}Cross-Platform Build Orchestrator${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

APP_NAME=$(python3 build_scripts/read_config.py branding.app_name_display 2>/dev/null || echo "Image-PDF Converter")
APP_VERSION=$(python3 build_scripts/read_config.py version.full 2>/dev/null || echo "1.0.0")
COMPANY_NAME=$(python3 build_scripts/read_config.py branding.company_name 2>/dev/null || echo "ImagePDF Solutions")

echo -e "${BLUE}Product:${NC} $APP_NAME"
echo -e "${BLUE}Version:${NC} $APP_VERSION"
echo -e "${BLUE}Company:${NC} $COMPANY_NAME"
echo ""

# Detect current platform
CURRENT_OS="unknown"
CURRENT_ARCH=$(uname -m)

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CURRENT_OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    CURRENT_OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    CURRENT_OS="windows"
fi

echo -e "${BLUE}Current Platform:${NC} $CURRENT_OS ($CURRENT_ARCH)"
echo ""

################################################################################
# Platform Build Status
################################################################################

CAN_BUILD_WINDOWS=false
CAN_BUILD_MACOS=false
CAN_BUILD_LINUX_X86=false
CAN_BUILD_LINUX_ARM=false

# Check what we can build on this machine
if [[ "$CURRENT_OS" == "linux" ]]; then
    if [[ "$CURRENT_ARCH" == "x86_64" ]]; then
        CAN_BUILD_LINUX_X86=true
        echo -e "${GREEN}✓${NC} Can build: Linux x86_64 (native)"
    elif [[ "$CURRENT_ARCH" == "aarch64" ]] || [[ "$CURRENT_ARCH" == "armv7l" ]]; then
        CAN_BUILD_LINUX_ARM=true
        echo -e "${GREEN}✓${NC} Can build: Linux ARM (native)"
    fi

    # Check for Docker (for cross-platform builds)
    if command -v docker &> /dev/null; then
        echo -e "${YELLOW}⚠${NC}  Docker available: Could attempt cross-platform Linux builds"
    fi

    echo -e "${YELLOW}⚠${NC}  Windows builds: Require Windows machine or Wine (not recommended)"
    echo -e "${YELLOW}⚠${NC}  macOS builds: Require macOS machine (cannot cross-compile)"

elif [[ "$CURRENT_OS" == "macos" ]]; then
    CAN_BUILD_MACOS=true
    echo -e "${GREEN}✓${NC} Can build: macOS (native)"
    echo -e "${YELLOW}⚠${NC}  Windows builds: Require Windows machine"
    echo -e "${YELLOW}⚠${NC}  Linux builds: Require Linux machine or Docker"

elif [[ "$CURRENT_OS" == "windows" ]]; then
    CAN_BUILD_WINDOWS=true
    echo -e "${GREEN}✓${NC} Can build: Windows (native)"
    echo -e "${YELLOW}⚠${NC}  macOS builds: Require macOS machine"
    echo -e "${YELLOW}⚠${NC}  Linux builds: Require Linux machine or WSL/Docker"
fi

echo ""

################################################################################
# Build Selection
################################################################################

echo -e "${CYAN}Select platforms to build:${NC}"
echo "  1) Build current platform only (recommended)"
echo "  2) Build all compatible platforms"
echo "  3) Custom selection"
echo "  4) Exit"
echo ""

read -p "Choice (1-4): " CHOICE

case $CHOICE in
    1)
        BUILD_CURRENT_ONLY=true
        ;;
    2)
        BUILD_ALL_COMPATIBLE=true
        ;;
    3)
        echo ""
        echo "Custom platform selection:"

        if [[ "$CAN_BUILD_LINUX_ARM" == true ]]; then
            read -p "Build Linux ARM? (y/n): " -n 1 -r; echo
            [[ $REPLY =~ ^[Yy]$ ]] && BUILD_LINUX_ARM=true
        fi

        if [[ "$CAN_BUILD_LINUX_X86" == true ]]; then
            read -p "Build Linux x86_64? (y/n): " -n 1 -r; echo
            [[ $REPLY =~ ^[Yy]$ ]] && BUILD_LINUX_X86=true
        fi

        if [[ "$CAN_BUILD_MACOS" == true ]]; then
            read -p "Build macOS? (y/n): " -n 1 -r; echo
            [[ $REPLY =~ ^[Yy]$ ]] && BUILD_MACOS=true
        fi

        if [[ "$CAN_BUILD_WINDOWS" == true ]]; then
            read -p "Build Windows? (y/n): " -n 1 -r; echo
            [[ $REPLY =~ ^[Yy]$ ]] && BUILD_WINDOWS=true
        fi
        ;;
    4)
        echo "Build cancelled"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

################################################################################
# Build Execution
################################################################################

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}Starting Build Process${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Create distribution directory
DIST_DIR="$PROJECT_ROOT/dist"
RELEASE_DIR="$DIST_DIR/release-$APP_VERSION"
mkdir -p "$RELEASE_DIR"

BUILD_COUNT=0
SUCCESS_COUNT=0
FAILED_BUILDS=()

# Function to build a platform
build_platform() {
    local platform=$1
    local script=$2
    local output_dir=$3

    echo ""
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}Building: $platform${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    BUILD_COUNT=$((BUILD_COUNT + 1))

    if bash "$script"; then
        echo -e "${GREEN}✓ $platform build successful${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

        # Copy to release directory
        if [ -d "$output_dir" ]; then
            echo "Copying to release directory..."
            cp -r "$output_dir"/* "$RELEASE_DIR/" 2>/dev/null || true
        fi
    else
        echo -e "${RED}✗ $platform build failed${NC}"
        FAILED_BUILDS+=("$platform")
    fi
}

# Build each selected platform
if [[ "$BUILD_CURRENT_ONLY" == true ]] || [[ "$BUILD_ALL_COMPATIBLE" == true ]]; then
    if [[ "$CAN_BUILD_LINUX_ARM" == true ]]; then
        build_platform "Linux ARM" \
            "$SCRIPT_DIR/linux_arm/build_linux_arm.sh" \
            "$DIST_DIR/linux_arm"
    fi

    if [[ "$CAN_BUILD_LINUX_X86" == true ]]; then
        build_platform "Linux x86_64" \
            "$SCRIPT_DIR/linux_x86/build_linux_x86.sh" \
            "$DIST_DIR/linux_x86"
    fi

    if [[ "$CAN_BUILD_MACOS" == true ]]; then
        build_platform "macOS" \
            "$SCRIPT_DIR/macos/build_macos.sh" \
            "$DIST_DIR/macos"
    fi

    if [[ "$CAN_BUILD_WINDOWS" == true ]]; then
        build_platform "Windows" \
            "$SCRIPT_DIR/windows/build_windows.bat" \
            "$DIST_DIR/windows"
    fi
else
    # Custom selection builds
    [[ "$BUILD_LINUX_ARM" == true ]] && build_platform "Linux ARM" \
        "$SCRIPT_DIR/linux_arm/build_linux_arm.sh" "$DIST_DIR/linux_arm"

    [[ "$BUILD_LINUX_X86" == true ]] && build_platform "Linux x86_64" \
        "$SCRIPT_DIR/linux_x86/build_linux_x86.sh" "$DIST_DIR/linux_x86"

    [[ "$BUILD_MACOS" == true ]] && build_platform "macOS" \
        "$SCRIPT_DIR/macos/build_macos.sh" "$DIST_DIR/macos"

    [[ "$BUILD_WINDOWS" == true ]] && build_platform "Windows" \
        "$SCRIPT_DIR/windows/build_windows.bat" "$DIST_DIR/windows"
fi

################################################################################
# Build Summary
################################################################################

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}Build Summary${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

echo -e "Attempted: $BUILD_COUNT"
echo -e "${GREEN}Succeeded: $SUCCESS_COUNT${NC}"

if [ ${#FAILED_BUILDS[@]} -gt 0 ]; then
    echo -e "${RED}Failed: ${#FAILED_BUILDS[@]}${NC}"
    echo ""
    echo "Failed builds:"
    for build in "${FAILED_BUILDS[@]}"; do
        echo -e "  ${RED}✗${NC} $build"
    done
fi

echo ""
echo -e "${BLUE}Distribution files:${NC}"
if [ -d "$RELEASE_DIR" ] && [ "$(ls -A $RELEASE_DIR)" ]; then
    ls -lh "$RELEASE_DIR"
    echo ""
    echo -e "${GREEN}Release directory: $RELEASE_DIR${NC}"
else
    echo -e "${YELLOW}No distribution files created${NC}"
fi

echo ""

# Generate checksums
if [ -d "$RELEASE_DIR" ] && [ "$(ls -A $RELEASE_DIR)" ]; then
    echo "Generating checksums..."
    cd "$RELEASE_DIR"
    sha256sum * > checksums.txt 2>/dev/null || true
    echo -e "${GREEN}✓ Checksums saved to checksums.txt${NC}"
    cd "$PROJECT_ROOT"
fi

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}Build process complete!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Instructions for platforms that couldn't be built
if [[ "$CAN_BUILD_WINDOWS" == false ]] && [[ "$BUILD_ALL_COMPATIBLE" == true ]]; then
    echo -e "${YELLOW}⚠ Windows build not available on this platform${NC}"
    echo "  To build for Windows:"
    echo "  1. Copy this project to a Windows machine"
    echo "  2. Run: build_scripts\\windows\\build_windows.bat"
    echo ""
fi

if [[ "$CAN_BUILD_MACOS" == false ]] && [[ "$BUILD_ALL_COMPATIBLE" == true ]]; then
    echo -e "${YELLOW}⚠ macOS build not available on this platform${NC}"
    echo "  To build for macOS:"
    echo "  1. Copy this project to a Mac"
    echo "  2. Run: bash build_scripts/macos/build_macos.sh"
    echo ""
fi

exit 0
