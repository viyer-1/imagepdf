#!/bin/bash
#
# Download Build Artifacts from GitHub Actions
#
# This script downloads pre-built executables from GitHub Actions to your local machine.
# Perfect for Raspberry Pi users who can't build Windows/macOS/Linux x86 locally.
#
# Prerequisites:
#   - GitHub CLI (gh) installed: https://cli.github.com/
#   - Authenticated with: gh auth login
#
# Usage:
#   ./build_scripts/download_builds.sh [workflow-run-id]
#
# If no run ID is provided, it will show recent workflow runs to choose from.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install it from: https://cli.github.com/"
    echo ""
    echo "On Raspberry Pi/Debian/Ubuntu:"
    echo "  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
    echo "  echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
    echo "  sudo apt update"
    echo "  sudo apt install gh"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo -e "${RED}Error: Not in a GitHub repository or remote not configured${NC}"
    echo "Make sure you're in the project directory and have pushed to GitHub"
    exit 1
fi

echo -e "${BLUE}Repository: $REPO${NC}"
echo ""

# Get version from config
VERSION=$(python3 build_scripts/read_config.py version.full 2>/dev/null || echo "unknown")

# If run ID not provided, show recent runs
if [ -z "$1" ]; then
    echo -e "${YELLOW}Recent workflow runs:${NC}"
    echo ""
    gh run list --workflow=build.yml --limit 10
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 <run-id>"
    echo ""
    echo "Example:"
    echo "  $0 1234567890"
    echo ""
    echo "Or download the latest successful run:"
    echo "  $0 latest"
    exit 0
fi

# Handle "latest" keyword
if [ "$1" = "latest" ]; then
    echo -e "${BLUE}Finding latest successful workflow run...${NC}"
    RUN_ID=$(gh run list --workflow=build.yml --status=success --limit=1 --json databaseId --jq '.[0].databaseId')
    if [ -z "$RUN_ID" ]; then
        echo -e "${RED}Error: No successful workflow runs found${NC}"
        exit 1
    fi
    echo -e "${GREEN}Found run ID: $RUN_ID${NC}"
else
    RUN_ID="$1"
fi

# Create download directory
DOWNLOAD_DIR="dist/downloaded-builds-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DOWNLOAD_DIR"

echo -e "${BLUE}Downloading artifacts from workflow run: $RUN_ID${NC}"
echo -e "${BLUE}Download directory: $DOWNLOAD_DIR${NC}"
echo ""

# Download all artifacts from the workflow run
cd "$DOWNLOAD_DIR"

echo -e "${YELLOW}Downloading artifacts...${NC}"
gh run download "$RUN_ID" --repo "$REPO"

# Check if consolidated release package exists
if [ -d "release-package-"* ]; then
    echo ""
    echo -e "${GREEN}Found consolidated release package!${NC}"
    RELEASE_DIR=$(ls -d release-package-* | head -1)

    # Move files from release package to main directory
    if [ -d "$RELEASE_DIR" ]; then
        mv "$RELEASE_DIR"/* .
        rmdir "$RELEASE_DIR"

        echo -e "${GREEN}✓ Moved release files to download directory${NC}"
    fi
fi

# Organize platform-specific builds
echo ""
echo -e "${YELLOW}Organizing build artifacts...${NC}"

# Count files
TOTAL_FILES=$(find . -type f \( -name "*.exe" -o -name "*.dmg" -o -name "*.AppImage" -o -name "*.tar.gz" \) | wc -l)

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo -e "${RED}Error: No build artifacts found${NC}"
    echo "The workflow may still be running or failed"
    exit 1
fi

# Display downloaded files
echo ""
echo -e "${GREEN}Downloaded build artifacts:${NC}"
echo ""

if [ -f "checksums.txt" ]; then
    echo -e "${BLUE}Checksums:${NC}"
    cat checksums.txt
    echo ""
fi

ls -lh *.exe 2>/dev/null && echo "" || true
ls -lh *.dmg 2>/dev/null && echo "" || true
ls -lh *.AppImage 2>/dev/null && echo "" || true
ls -lh *.tar.gz 2>/dev/null && echo "" || true

# Make AppImages executable
if ls *.AppImage 1> /dev/null 2>&1; then
    chmod +x *.AppImage
    echo -e "${GREEN}✓ Made AppImages executable${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Download complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Build artifacts location:${NC}"
echo -e "  ${BLUE}$(pwd)${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify checksums: sha256sum -c checksums.txt"
echo "  2. Test the executables on their target platforms"
echo "  3. Distribute to users or upload to release server"
echo ""

# Return to original directory
cd - > /dev/null

echo -e "${BLUE}Tip:${NC} To download the latest successful build automatically:"
echo -e "  ${GREEN}./build_scripts/download_builds.sh latest${NC}"
echo ""
