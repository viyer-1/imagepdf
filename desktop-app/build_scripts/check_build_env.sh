#!/bin/bash
################################################################################
# Build Environment Checker
# Verifies that the build environment is properly configured
################################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo "Build Environment Check"
echo "============================================"
echo ""

ISSUES=0
WARNINGS=0

# Check if in venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}✗ Not in a virtual environment${NC}"
    echo "  You should activate your venv first: source ~/.venvs/main/bin/activate"
    ISSUES=$((ISSUES + 1))
else
    echo -e "${GREEN}✓ Virtual environment active: $VIRTUAL_ENV${NC}"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "  Python version: $PYTHON_VERSION"

# Check if required packages are installed
echo ""
echo "Checking required Python packages..."

REQUIRED_PACKAGES=("PyQt6" "PIL" "reportlab" "fitz" "flask" "werkzeug" "pyinstaller")

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
        echo -e "${GREEN}✓ $pkg${NC}"
    else
        echo -e "${RED}✗ $pkg not installed${NC}"
        ISSUES=$((ISSUES + 1))
    fi
done

# Check for bloat packages that will increase build size
echo ""
echo "Checking for unnecessary packages (these will be excluded from build)..."

BLOAT_PACKAGES=("torch" "tensorflow" "scipy" "pandas" "sklearn")

for pkg in "${BLOAT_PACKAGES[@]}"; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
        echo -e "${YELLOW}⚠ $pkg found (will be excluded from build)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check disk space
echo ""
echo "Checking disk space..."
AVAILABLE_SPACE=$(df -h . | tail -1 | awk '{print $4}')
echo "  Available space: $AVAILABLE_SPACE"

# Check architecture
echo ""
echo "System information:"
echo "  Architecture: $(uname -m)"
echo "  OS: $(uname -s)"
echo "  Kernel: $(uname -r)"

# Summary
echo ""
echo "============================================"
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ Build environment is ready!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Note: $WARNINGS unnecessary packages found${NC}"
        echo "These will be excluded from the build automatically."
    fi
else
    echo -e "${RED}✗ $ISSUES issues found${NC}"
    echo "Please fix the issues above before building."
    exit 1
fi
echo "============================================"
echo ""

exit 0
