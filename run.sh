#!/bin/bash
# run.sh - Portable startup script matching IntelliJ configuration

set -e

# 1. Determine Project Root (where this script is located)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Set Working Directory to 'src' (matches IntelliJ "Working directory")
cd "$PROJECT_ROOT/src"

echo "HardwareGUI Startup"
echo "==================="
echo "Working Directory: $(pwd)"

# Warn about existing virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "[ERROR] You are currently in a virtual environment: $VIRTUAL_ENV"
    echo "        Please deactivate it first with: deactivate"
    echo "        Then run this script again."
    exit 1
fi

# 3. Configure PYTHONPATH (matches IntelliJ "Add content/source roots")
# - PROJECT_ROOT (Content Root)
# - PROJECT_ROOT/src (Source Root)
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src"

# 4. Add ALL DPI package directories to PYTHONPATH
# This ensures imports work even if editable installs have issues
DPI_PACKAGES=(
    "/measdata/dpi/dpi"
    "/measdata/dpi/arrayextensionunit/python"
    "/measdata/dpi/maincontrolunit/python"
    "/measdata/dpi/powersupplyunit/python"
    "/measdata/dpi/samplingunit/python"
    "/measdata/dpi/samplingunit/python/dev"
    "/measdata/dpi/sourcemeasureunit/python"
    "/measdata/dpi/sourcemeasureunit/python/dev"
    "/measdata/dpi/voltageunit/python"
    "/measdata/dpi/voltageunit/python/dev"
)

for pkg in "${DPI_PACKAGES[@]}"; do
    if [ -d "$pkg" ]; then
        export PYTHONPATH="$pkg:$PYTHONPATH"
    fi
done

echo "[OK] PYTHONPATH configured with all DPI packages"

# 5. Set Environment Variables (matches IntelliJ)
export PYTHONUNBUFFERED=1

# 6. Check for uv
if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv is not installed"
    exit 1
fi

# 7. Run the application
echo "Starting main.py..."
echo ""
uv run python main.py
